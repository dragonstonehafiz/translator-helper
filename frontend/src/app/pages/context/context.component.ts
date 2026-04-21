import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StateService, StoredTaskState, TASK_TYPES, TaskProgress } from '../../services/state.service';
import { ApiService } from '../../services/api.service';
import { Observable, Subscription, interval } from 'rxjs';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { ContextStatusComponent } from '../../components/context-status/context-status.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { DownloadsListComponent } from '../../components/downloads-list/downloads-list.component';
import { ConfirmationService } from '../../services/confirmation.service';
import { ActiveSubtitlePanelComponent } from '../../components/active-subtitle-panel/active-subtitle-panel.component';
import { LANGUAGE_OPTIONS } from '../../shared/language-options';
import { ErrorDialogService } from '../../services/error-dialog.service';

@Component({
  selector: 'app-context',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, FileUploadComponent, TextFieldComponent, TooltipIconComponent, ContextStatusComponent, LoadingTextIndicatorComponent, PrimaryButtonComponent, DownloadsListComponent, ActiveSubtitlePanelComponent],
  templateUrl: './context.component.html',
  styleUrl: './context.component.scss'
})
export class ContextComponent implements OnInit, OnDestroy {
  private readonly defaultTaskProgress = {
    [TASK_TYPES.generateCharacterList]: { current: 0, total: 1, status: 'Generating character list from the subtitle file', eta_seconds: 0 },
    [TASK_TYPES.generateSynopsis]: { current: 0, total: 1, status: 'Generating synopsis from the subtitle file', eta_seconds: 0 },
    [TASK_TYPES.generateSummary]: { current: 0, total: 1, status: 'Generating summary from the subtitle file', eta_seconds: 0 },
  } as const;

  characterList = '';
  synopsis = '';
  summary = '';
  additionalInstructions = '';
  selectedFile: File | null = null;
  currentFilename: string | null = null;
  inputLanguage = 'ja';
  outputLanguage = 'en';

  // Context files downloads list
  availableContextFiles: {name: string, size: number, modified: string}[] = [];
  isFetchingContextFiles = false;
  deletingContextFile = '';
  private pollingSubscription?: Subscription;
  private taskStateSubscription?: Subscription;
  private subtitleFileSubscription?: Subscription;
  private contentStateSubscription?: Subscription;
  private activePollingTaskType: string | null = null;
  private lastShownTaskError: Record<string, string> = {};
  
  // Context checkboxes for character list generation
  characterListUseAdditionalInstructions = true;
  
  // Context checkboxes for synopsis generation
  synopsisUseAdditionalInstructions = true;
  synopsisUseCharacterList = true;
  
  // Context checkboxes for summary generation
  summaryUseAdditionalInstructions = true;
  summaryUseCharacterList = true;

  isGeneratingCharacterList = false;
  isGeneratingSynopsis = false;
  isGeneratingSummary = false;

  activeContextTab: 'additional' | 'character' | 'synopsis' | 'summary' = 'additional';
  
  languageOptions = LANGUAGE_OPTIONS;

  constructor(
    private stateService: StateService,
    private apiService: ApiService,
    private confirmationService: ConfirmationService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.contentStateSubscription = this.stateService.contentState$.subscribe(state => {
      this.characterList = state.characterList;
      this.synopsis = state.synopsis;
      this.summary = state.summary;
      this.additionalInstructions = state.additionalInstructions;
    });
    this.taskStateSubscription = this.stateService.taskStates$.subscribe(() => {
      this.syncGenerationFlags();
    });
    this.syncGenerationFlags();
    this.resumePollingIfNeeded();
    this.syncActiveSubtitleFile(this.stateService.getActiveSubtitleFile());
    this.subtitleFileSubscription = this.stateService.activeSubtitleFile$.subscribe(file => {
      this.syncActiveSubtitleFile(file);
    });

    this.refreshContextFiles();
  }

  ngOnDestroy(): void {
    this.stopPolling();
    this.taskStateSubscription?.unsubscribe();
    this.subtitleFileSubscription?.unsubscribe();
    this.contentStateSubscription?.unsubscribe();
  }

  startPolling(taskType: string): void {
    if (this.activePollingTaskType === taskType && this.pollingSubscription) {
      return;
    }
    this.stopPolling();
    this.activePollingTaskType = taskType;
    this.pollingSubscription = interval(1000).subscribe(() => {
      this.apiService.getTaskResult(taskType).subscribe({
        next: (response) => {
          const taskData = response.data;
          this.updateTaskStateFromResponse(taskType, response.status, taskData?.result ?? null, response.message, taskData?.progress ?? null);
          if (response.status === 'complete' && taskData?.result) {
            this.applyContextResult(taskType, taskData.result.text ?? '');
            this.saveContext();
            this.stopPolling();
          } else if (response.status === 'error' || response.status === 'idle') {
            if (response.status === 'error' && response.message) {
              this.showTaskError(taskType, response.message);
            }
            this.stopPolling();
          }
        },
        error: (err) => console.error('Error checking running status:', err)
      });
    });
  }

  stopPolling(): void {
    this.pollingSubscription?.unsubscribe();
    this.pollingSubscription = undefined;
    this.activePollingTaskType = null;
  }

  updateCharacterList(): void {
    this.stateService.setCharacterList(this.characterList);
    this.saveContext();
  }

  updateSynopsis(): void {
    this.stateService.setSynopsis(this.synopsis);
    this.saveContext();
  }

  updateSummary(): void {
    this.stateService.setSummary(this.summary);
    this.saveContext();
  }

  updateAdditionalInstructions(): void {
    this.stateService.setAdditionalInstructions(this.additionalInstructions);
    this.saveContext();
  }

  setContextTab(tab: 'additional' | 'character' | 'synopsis' | 'summary'): void {
    this.activeContextTab = tab;
  }

  generateCharacterList(): void {
    if (!this.selectedFile) {
      this.errorDialogService.show('Please upload a subtitle file first');
      return;
    }

    if (this.stateService.hasActiveTask()) {
      return;
    }

    // Build context dict with only checked and non-empty fields
    const context: any = {};
    if (this.characterListUseAdditionalInstructions && this.additionalInstructions.trim()) {
      context.additional_instructions = this.additionalInstructions;
    }
    
    this.startContextTask(
      TASK_TYPES.generateCharacterList,
      this.apiService.generateCharacterList(
      this.selectedFile,
      context,
      this.inputLanguage,
      this.outputLanguage
    ));
  }

  generateSynopsis(): void {
    if (!this.selectedFile) {
      this.errorDialogService.show('Please upload a subtitle file first');
      return;
    }

    if (this.stateService.hasActiveTask()) {
      return;
    }

    // Build context dict with only checked and non-empty fields
    const context: any = {};
    if (this.synopsisUseAdditionalInstructions && this.additionalInstructions.trim()) {
      context.additional_instructions = this.additionalInstructions;
    }
    if (this.synopsisUseCharacterList && this.characterList.trim()) {
      context.character_list = this.characterList;
    }
    
    this.startContextTask(
      TASK_TYPES.generateSynopsis,
      this.apiService.generateSynopsis(
      this.selectedFile,
      context,
      this.inputLanguage,
      this.outputLanguage
    ));
  }

  generateSummary(): void {
    if (!this.selectedFile) {
      this.errorDialogService.show('Please upload a subtitle file first');
      return;
    }

    if (this.stateService.hasActiveTask()) {
      return;
    }

    // Build context dict with only checked and non-empty fields
    const context: any = {};
    if (this.summaryUseAdditionalInstructions && this.additionalInstructions.trim()) {
      context.additional_instructions = this.additionalInstructions;
    }
    if (this.summaryUseCharacterList && this.characterList.trim()) {
      context.character_list = this.characterList;
    }
    
    this.startContextTask(
      TASK_TYPES.generateSummary,
      this.apiService.generateSummary(
      this.selectedFile,
      context,
      this.inputLanguage,
      this.outputLanguage
    ));
  }

  saveContext(): void {
    if (!this.currentFilename) return;
    const context = {
      inputLanguage: this.inputLanguage,
      outputLanguage: this.outputLanguage,
      characterList: this.characterList,
      synopsis: this.synopsis,
      summary: this.summary,
      additionalInstructions: this.additionalInstructions,
    };
    this.apiService.saveContext(this.currentFilename, context).subscribe({
      next: () => this.refreshContextFiles(),
      error: (err) => console.error('Failed to save context:', err)
    });
  }

  refreshContextFiles(): void {
    this.isFetchingContextFiles = true;
    this.apiService.listFiles('context-files').subscribe({
      next: (response) => {
        this.availableContextFiles = response.data?.files ?? [];
        this.isFetchingContextFiles = false;
      },
      error: (err) => {
        console.error('Error fetching context files:', err);
        this.isFetchingContextFiles = false;
      }
    });
  }

  downloadContextFile(filename: string): void {
    if (!filename) return;
    this.apiService.getFileBlob('context-files', filename).subscribe({
      next: (blob) => {
        this.triggerDownload(blob, filename);
      },
      error: (err) => {
        console.error('Error downloading context file:', err);
        this.errorDialogService.show('Failed to download context file. Please try again.');
      }
    });
  }

  async deleteContextFile(filename: string): Promise<void> {
    if (!filename || this.deletingContextFile) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Confirm Deletion',
      message: `Delete ${filename}? This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.deletingContextFile = filename;
    this.apiService.deleteFile('context-files', filename).subscribe({
      next: () => {
        this.deletingContextFile = '';
        this.refreshContextFiles();
      },
      error: (err) => {
        console.error('Error deleting context file:', err);
        this.deletingContextFile = '';
      }
    });
  }

  async onImportFilesSelected(files: File[]): Promise<void> {
    if (files.length === 0) return;
    const file = files[0];
    if (!file.name.endsWith('.json')) {
      this.errorDialogService.show('Please select a JSON file.');
      return;
    }
    if (!this.currentFilename) {
      this.errorDialogService.show('Please upload a subtitle file first before importing context.');
      return;
    }
    const existingFile = this.availableContextFiles.find(f => f.name === this.currentFilename);
    if (existingFile) {
      const confirmed = await this.confirmationService.confirm({
        title: 'Overwrite Context File',
        message: `This will overwrite the existing context file "${this.currentFilename}".`,
        confirmLabel: 'Overwrite',
        cancelLabel: 'Cancel',
      });
      if (!confirmed) return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (data.inputLanguage !== undefined) this.inputLanguage = data.inputLanguage;
        if (data.outputLanguage !== undefined) this.outputLanguage = data.outputLanguage;
        if (data.characterList !== undefined) {
          this.characterList = data.characterList;
          this.stateService.setCharacterList(data.characterList);
        }
        if (data.synopsis !== undefined) {
          this.synopsis = data.synopsis;
          this.stateService.setSynopsis(data.synopsis);
        }
        if (data.summary !== undefined) {
          this.summary = data.summary;
          this.stateService.setSummary(data.summary);
        }
        if (data.additionalInstructions !== undefined) {
          this.additionalInstructions = data.additionalInstructions;
          this.stateService.setAdditionalInstructions(data.additionalInstructions);
        }
        this.saveContext();
      } catch (error) {
        console.error('Error parsing import file:', error);
        this.errorDialogService.show('Failed to import context. Invalid JSON file.');
      }
    };
    reader.readAsText(file);
  }

  isAnyTaskRunning(): boolean {
    return this.stateService.hasActiveTask();
  }

  private startContextTask(taskType: string, request$: Observable<{status: string, message: string | null}>): void {
    this.stateService.setTaskState(taskType, {
      status: 'processing',
      result: null,
      message: null,
      progress: this.defaultProgress(taskType as keyof typeof this.defaultTaskProgress),
      isPolling: false,
    });
    request$.subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          this.stateService.setTaskState(taskType, { isPolling: true });
          this.startPolling(taskType);
        } else {
          this.stateService.setTaskState(taskType, {
            status: 'error',
            message: response.message || 'Failed to start task.',
            isPolling: false,
          });
          this.errorDialogService.show({
            title: 'Error',
            message: response.message || 'Failed to start task.',
          });
          this.stopPolling();
        }
      },
      error: (err) => {
        console.error('Error starting context task:', err);
        this.stateService.setTaskState(taskType, {
          status: 'error',
          message: 'Failed to start context task. Please try again.',
          isPolling: false,
        });
        this.errorDialogService.show('Failed to start context task. Please try again.');
        this.stopPolling();
      }
    });
  }

  private syncGenerationFlags(): void {
    this.isGeneratingCharacterList = this.isTaskProcessing(TASK_TYPES.generateCharacterList);
    this.isGeneratingSynopsis = this.isTaskProcessing(TASK_TYPES.generateSynopsis);
    this.isGeneratingSummary = this.isTaskProcessing(TASK_TYPES.generateSummary);
  }

  private isTaskProcessing(taskType: string): boolean {
    return this.stateService.getTaskState(taskType).status === 'processing';
  }

  private resumePollingIfNeeded(): void {
    const taskTypes = [
      TASK_TYPES.generateCharacterList,
      TASK_TYPES.generateSynopsis,
      TASK_TYPES.generateSummary,
    ];
    const resumableTask = taskTypes.find(taskType => {
      const taskState = this.stateService.getTaskState(taskType);
      return taskState.status === 'processing' || taskState.isPolling;
    });
    if (resumableTask) {
      this.startPolling(resumableTask);
    }
  }

  private updateTaskStateFromResponse(
    taskType: string,
    status: string,
    result?: {text?: string} | null,
    message?: string | null,
    progress?: TaskProgress | null,
  ): void {
    this.stateService.setTaskState(taskType, {
      status: (status === 'idle' ? 'idle' : status) as StoredTaskState['status'],
      result: result ?? null,
      message: message ?? null,
      progress: progress ?? this.stateService.getTaskState(taskType).progress,
      isPolling: status === 'processing',
    });
  }

  private defaultProgress(taskType: keyof typeof this.defaultTaskProgress): TaskProgress {
    return {
      task_type: taskType,
      ...this.defaultTaskProgress[taskType],
    };
  }

  private showTaskError(taskType: string, message: string): void {
    if (this.lastShownTaskError[taskType] === message) {
      return;
    }
    this.lastShownTaskError[taskType] = message;
    this.errorDialogService.show(message);
  }

  private syncActiveSubtitleFile(file: File | null): void {
    if (this.selectedFile === file) {
      return;
    }

    this.selectedFile = file;
    if (!file) {
      this.currentFilename = null;
      return;
    }

    const baseName = file.name.replace(/\.(ass|srt)$/i, '');
    this.currentFilename = `${baseName}.json`;
    this.refreshContextFiles();
  }

  private applyContextResult(taskType: string, data: string): void {
    if (taskType === TASK_TYPES.generateCharacterList) {
      this.characterList = data;
      this.stateService.setCharacterList(data);
    } else if (taskType === TASK_TYPES.generateSynopsis) {
      this.synopsis = data;
      this.stateService.setSynopsis(data);
    } else if (taskType === TASK_TYPES.generateSummary) {
      this.summary = data;
      this.stateService.setSummary(data);
    }
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
  }

}
