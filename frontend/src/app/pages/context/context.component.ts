import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StateService, StoredTaskState, TASK_TYPES } from '../../services/state.service';
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

@Component({
  selector: 'app-context',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, FileUploadComponent, TextFieldComponent, TooltipIconComponent, ContextStatusComponent, LoadingTextIndicatorComponent, PrimaryButtonComponent, DownloadsListComponent],
  templateUrl: './context.component.html',
  styleUrl: './context.component.scss'
})
export class ContextComponent implements OnInit, OnDestroy {
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
  private activePollingTaskType: string | null = null;
  
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
  isGeneratingRecap = false;

  activeContextTab: 'additional' | 'character' | 'synopsis' | 'summary' = 'additional';
  
  // Recap section
  recap = '';
  recapContextFiles: File[] = [];
  recapContexts: any[] = [];
  
  languageOptions = [
    { code: 'en', name: 'English' },
    { code: 'ja', name: 'Japanese' },
    { code: 'zh', name: 'Chinese' },
    { code: 'ko', name: 'Korean' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'de', name: 'German' },
    { code: 'it', name: 'Italian' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'ru', name: 'Russian' },
    { code: 'ar', name: 'Arabic' },
    { code: 'hi', name: 'Hindi' },
    { code: 'th', name: 'Thai' },
    { code: 'vi', name: 'Vietnamese' },
    { code: 'id', name: 'Indonesian' },
    { code: 'nl', name: 'Dutch' },
    { code: 'pl', name: 'Polish' },
    { code: 'tr', name: 'Turkish' },
    { code: 'sv', name: 'Swedish' },
    { code: 'da', name: 'Danish' },
    { code: 'fi', name: 'Finnish' },
    { code: 'no', name: 'Norwegian' },
    { code: 'cs', name: 'Czech' },
    { code: 'el', name: 'Greek' },
    { code: 'he', name: 'Hebrew' },
    { code: 'hu', name: 'Hungarian' },
    { code: 'ro', name: 'Romanian' },
    { code: 'uk', name: 'Ukrainian' }
  ];

  constructor(private stateService: StateService, private apiService: ApiService) {}

  ngOnInit(): void {
    // Load existing values from state
    this.characterList = this.stateService.getCharacterList();
    this.synopsis = this.stateService.getSynopsis();
    this.summary = this.stateService.getSummary();
    this.recap = this.stateService.getRecap();
    this.additionalInstructions = this.stateService.getAdditionalInstructions();
    this.taskStateSubscription = this.stateService.taskStates$.subscribe(() => {
      this.syncGenerationFlags();
    });
    this.syncGenerationFlags();
    this.resumePollingIfNeeded();

    this.refreshContextFiles();
  }

  ngOnDestroy(): void {
    this.stopPolling();
    this.taskStateSubscription?.unsubscribe();
  }

  startPolling(taskType: string): void {
    if (this.activePollingTaskType === taskType && this.pollingSubscription) {
      return;
    }
    this.stopPolling();
    this.activePollingTaskType = taskType;
    this.pollingSubscription = interval(1000).subscribe(() => {
      this.apiService.getContextResult(taskType).subscribe({
        next: (response) => {
          this.updateTaskStateFromResponse(taskType, response.status, response.result, response.message);
          if (response.status === 'complete' && response.result) {
            this.applyContextResult(response.result.type, response.result.data ?? '');
            this.saveContext();
            this.stopPolling();
          } else if (response.status === 'error' || response.status === 'idle') {
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

  onSubtitleFilesSelected(files: File[]): void {
    if (files.length > 0) {
      const file = files[0];
      if (file.name.endsWith('.ass') || file.name.endsWith('.srt')) {
        this.selectedFile = file;
        const baseName = file.name.replace(/\.(ass|srt)$/i, '');
        this.currentFilename = `${baseName}.json`;
        this.refreshContextFiles();
        this.loadContextFromFile(this.currentFilename);
      } else {
        alert('Please select an .ass or .srt file.');
      }
    }
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

  updateRecap(): void {
    this.stateService.setRecap(this.recap);
    this.saveContext();
  }

  setContextTab(tab: 'additional' | 'character' | 'synopsis' | 'summary'): void {
    this.activeContextTab = tab;
  }

  hasContent(value: string): boolean {
    return !!value && value.trim().length > 0;
  }

  hasAnyContextContent(): boolean {
    return this.hasContent(this.additionalInstructions)
      || this.hasContent(this.characterList)
      || this.hasContent(this.synopsis)
      || this.hasContent(this.summary);
  }

  generateCharacterList(): void {
    if (!this.selectedFile) {
      alert('Please upload a subtitle file first');
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
      alert('Please upload a subtitle file first');
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
      alert('Please upload a subtitle file first');
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
      recap: this.recap,
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
        this.availableContextFiles = response.files;
        this.isFetchingContextFiles = false;
      },
      error: (err) => {
        console.error('Error fetching context files:', err);
        this.isFetchingContextFiles = false;
      }
    });
  }

  loadContextFromFile(filename: string): void {
    this.apiService.downloadFile('context-files', filename).subscribe({
      next: (blob) => {
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
            if (data.recap !== undefined) {
              this.recap = data.recap;
              this.stateService.setRecap(data.recap);
            }
            if (data.additionalInstructions !== undefined) {
              this.additionalInstructions = data.additionalInstructions;
              this.stateService.setAdditionalInstructions(data.additionalInstructions);
            }
          } catch (error) {
            console.error('Error parsing context file:', error);
            alert('Failed to load context file.');
          }
        };
        reader.readAsText(blob);
      },
      error: (err) => {
        if (err.status !== 404) {
          console.error('Error loading context file:', err);
          alert('Failed to load context file.');
        }
      }
    });
  }

  deleteContextFile(filename: string): void {
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

  onImportFilesSelected(files: File[]): void {
    if (files.length === 0) return;
    const file = files[0];
    if (!file.name.endsWith('.json')) {
      alert('Please select a JSON file.');
      return;
    }
    if (!this.currentFilename) {
      alert('Please upload a subtitle file first before importing context.');
      return;
    }
    const existingFile = this.availableContextFiles.find(f => f.name === this.currentFilename);
    if (existingFile) {
      const confirmed = confirm(`This will overwrite the existing context file "${this.currentFilename}". Are you sure?`);
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
        if (data.recap !== undefined) {
          this.recap = data.recap;
          this.stateService.setRecap(data.recap);
        }
        if (data.additionalInstructions !== undefined) {
          this.additionalInstructions = data.additionalInstructions;
          this.stateService.setAdditionalInstructions(data.additionalInstructions);
        }
        this.saveContext();
      } catch (error) {
        console.error('Error parsing import file:', error);
        alert('Failed to import context. Invalid JSON file.');
      }
    };
    reader.readAsText(file);
  }

  onRecapFilesSelected(files: File[]): void {
    const jsonFiles = files.filter(file => file.name.endsWith('.json'));
    if (jsonFiles.length > 0) {
      this.recapContextFiles = jsonFiles;
      this.loadRecapContextFiles();
    } else if (files.length > 0) {
      alert('Please select JSON files.');
    }
  }

  private loadRecapContextFiles(): void {
    this.recapContexts = [];
    const promises: Promise<any>[] = [];

    for (const file of this.recapContextFiles) {
      const promise = new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const data = JSON.parse(e.target?.result as string);
            resolve(data);
          } catch (error) {
            console.error(`Error parsing ${file.name}:`, error);
            reject(error);
          }
        };
        reader.onerror = () => reject(new Error(`Failed to read ${file.name}`));
        reader.readAsText(file);
      });
      promises.push(promise);
    }

    Promise.all(promises)
      .then(contexts => {
        this.recapContexts = contexts;
      })
      .catch(error => {
        console.error('Error loading context files:', error);
        alert('Failed to load some context files.');
      });
  }

  removeRecapFile(index: number): void {
    this.recapContextFiles.splice(index, 1);
    this.recapContexts.splice(index, 1);
  }

  moveRecapFileUp(index: number): void {
    if (index > 0) {
      // Swap files
      [this.recapContextFiles[index], this.recapContextFiles[index - 1]] = 
        [this.recapContextFiles[index - 1], this.recapContextFiles[index]];
      
      // Swap contexts if they exist
      if (this.recapContexts.length > index) {
        [this.recapContexts[index], this.recapContexts[index - 1]] = 
          [this.recapContexts[index - 1], this.recapContexts[index]];
      }
    }
  }

  moveRecapFileDown(index: number): void {
    if (index < this.recapContextFiles.length - 1) {
      // Swap files
      [this.recapContextFiles[index], this.recapContextFiles[index + 1]] = 
        [this.recapContextFiles[index + 1], this.recapContextFiles[index]];
      
      // Swap contexts if they exist
      if (this.recapContexts.length > index + 1) {
        [this.recapContexts[index], this.recapContexts[index + 1]] = 
          [this.recapContexts[index + 1], this.recapContexts[index]];
      }
    }
  }

  generateRecap(): void {
    if (this.recapContexts.length === 0) {
      alert('Please upload at least one context file');
      return;
    }

    if (this.stateService.hasActiveTask()) {
      return;
    }
    this.startContextTask(
      TASK_TYPES.generateRecap,
      this.apiService.generateRecap(
      this.recapContexts,
      this.inputLanguage,
      this.outputLanguage
    ));
  }

  isAnyTaskRunning(): boolean {
    return this.stateService.hasActiveTask();
  }

  private startContextTask(taskType: string, request$: Observable<{status: string, message?: string}>): void {
    this.stateService.setTaskState(taskType, {
      status: 'processing',
      result: null,
      message: null,
      progress: null,
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
          alert(`Error: ${response.message}`);
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
        alert('Failed to start context task. Please try again.');
        this.stopPolling();
      }
    });
  }

  private syncGenerationFlags(): void {
    this.isGeneratingCharacterList = this.isTaskProcessing(TASK_TYPES.generateCharacterList);
    this.isGeneratingSynopsis = this.isTaskProcessing(TASK_TYPES.generateSynopsis);
    this.isGeneratingSummary = this.isTaskProcessing(TASK_TYPES.generateSummary);
    this.isGeneratingRecap = this.isTaskProcessing(TASK_TYPES.generateRecap);
  }

  private isTaskProcessing(taskType: string): boolean {
    return this.stateService.getTaskState(taskType).status === 'processing';
  }

  private resumePollingIfNeeded(): void {
    const taskTypes = [
      TASK_TYPES.generateCharacterList,
      TASK_TYPES.generateSynopsis,
      TASK_TYPES.generateSummary,
      TASK_TYPES.generateRecap,
    ];
    const resumableTask = taskTypes.find(taskType => {
      const taskState = this.stateService.getTaskState(taskType);
      return taskState.status === 'processing' || taskState.isPolling;
    });
    if (resumableTask) {
      this.startPolling(resumableTask);
    }
  }

  private updateTaskStateFromResponse(taskType: string, status: string, result?: {type: string, data?: string} | null, message?: string): void {
    this.stateService.setTaskState(taskType, {
      status: (status === 'idle' ? 'idle' : status) as StoredTaskState['status'],
      result: result ?? null,
      message: message ?? null,
      isPolling: status === 'processing',
    });
  }

  private applyContextResult(type: string, data: string): void {
    if (type === 'character_list') {
      this.characterList = data;
      this.stateService.setCharacterList(data);
    } else if (type === 'synopsis') {
      this.synopsis = data;
      this.stateService.setSynopsis(data);
    } else if (type === 'summary') {
      this.summary = data;
      this.stateService.setSummary(data);
    } else if (type === 'recap') {
      this.recap = data;
      this.stateService.setRecap(data);
    }
  }

}
