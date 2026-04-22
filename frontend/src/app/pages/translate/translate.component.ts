import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { ContextStatusComponent } from '../../components/context-status/context-status.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { DownloadsListComponent } from '../../components/downloads-list/downloads-list.component';
import { ApiService, TaskResultResponse } from '../../services/api.service';
import { StateService, TASK_TYPES, TaskProgress } from '../../services/state.service';
import { ConfirmationService } from '../../services/confirmation.service';
import { ActiveSubtitlePanelComponent } from '../../components/active-subtitle-panel/active-subtitle-panel.component';
import { LANGUAGE_OPTIONS } from '../../shared/language-options';
import { ErrorDialogService } from '../../services/error-dialog.service';

@Component({
  selector: 'app-translate',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, TextFieldComponent, TooltipIconComponent, ContextStatusComponent, PrimaryButtonComponent, LoadingTextIndicatorComponent, DownloadsListComponent, ActiveSubtitlePanelComponent],
  templateUrl: './translate.component.html',
  styleUrl: './translate.component.scss'
})
export class TranslateComponent implements OnInit, OnDestroy {
  private readonly defaultTaskProgress = {
    [TASK_TYPES.translateLine]: { current: 0, total: 1, status: 'Translating the entered text', eta_seconds: 0 },
    [TASK_TYPES.translateFile]: { current: 0, total: 1, status: 'Preparing subtitle file translation', eta_seconds: 0 },
    [TASK_TYPES.reviewTranslatedFile]: { current: 0, total: 1, status: 'Preparing translation review', eta_seconds: 0 },
  } as const;

  // Context data
  characterList = '';
  synopsis = '';
  summary = '';
  additionalInstructions = '';
  activeContextTab: 'additional' | 'character' | 'synopsis' | 'summary' = 'additional';

  // Translate Line
  lineUseAdditionalInstructions = false;
  lineUseCharacterList = false;
  lineUseSynopsis = false;
  lineUseSummary = false;
  lineInputLanguage = 'ja';
  lineOutputLanguage = 'en';
  lineTextToTranslate = '';
  lineTranslationResult = '';
  isTranslatingLine = false;
  private linePollingInterval?: any;

  // Translate File
  fileUseAdditionalInstructions = false;
  fileUseCharacterList = false;
  fileUseSynopsis = false;
  fileUseSummary = false;
  fileInputLanguage = 'ja';
  fileOutputLanguage = 'en';
  batchSize = 50;
  fileToTranslate: File | null = null;
  translatedFileToReview: File | null = null;
  isTranslatingFile = false;
  isReviewingTranslatedFile = false;
  availableDownloads: { name: string; size: number; modified: string }[] = [];
  isFetchingDownloads = false;
  downloadError = '';
  deletingDownload = '';
  private filePollingInterval?: any;
  private reviewPollingInterval?: any;
  private lastShownTaskError: Record<string, string> = {};
  private subtitleFileSubscription?: Subscription;
  private translatedSubtitleFileSubscription?: Subscription;
  private contentStateSubscription?: Subscription;

  languageOptions = LANGUAGE_OPTIONS;

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
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
    this.fileToTranslate = this.stateService.getActiveSubtitleFile();
    this.subtitleFileSubscription = this.stateService.activeSubtitleFile$.subscribe(file => {
      this.fileToTranslate = file;
    });
    this.translatedFileToReview = this.stateService.getActiveTranslatedSubtitleFile();
    this.translatedSubtitleFileSubscription = this.stateService.activeTranslatedSubtitleFile$.subscribe(file => {
      this.translatedFileToReview = file;
    });
    this.restoreTaskState();
    this.refreshDownloads();
  }

  ngOnDestroy(): void {
    this.stopLinePolling();
    this.stopFilePolling();
    this.stopReviewPolling();
    this.subtitleFileSubscription?.unsubscribe();
    this.translatedSubtitleFileSubscription?.unsubscribe();
    this.contentStateSubscription?.unsubscribe();
  }

  private restoreTaskState(): void {
    const lineTask = this.stateService.getTaskState(TASK_TYPES.translateLine);
    const fileTask = this.stateService.getTaskState(TASK_TYPES.translateFile);
    const reviewTask = this.stateService.getTaskState(TASK_TYPES.reviewTranslatedFile);

    this.isTranslatingLine = lineTask.status === 'processing';
    this.lineTranslationResult = lineTask.result?.text ?? '';

    this.isTranslatingFile = fileTask.status === 'processing';
    this.isReviewingTranslatedFile = reviewTask.status === 'processing';

    if (lineTask.status === 'processing' || lineTask.isPolling) {
      this.startLinePolling();
    }
    if (fileTask.status === 'processing' || fileTask.isPolling) {
      this.startFilePolling();
    }
    if (reviewTask.status === 'processing' || reviewTask.isPolling) {
      this.startReviewPolling();
    }
  }

  setContextTab(tab: 'additional' | 'character' | 'synopsis' | 'summary'): void {
    this.activeContextTab = tab;
  }

  updateAdditionalInstructions(): void {
    this.stateService.setAdditionalInstructions(this.additionalInstructions);
  }

  updateCharacterList(): void {
    this.stateService.setCharacterList(this.characterList);
  }

  updateSynopsis(): void {
    this.stateService.setSynopsis(this.synopsis);
  }

  updateSummary(): void {
    this.stateService.setSummary(this.summary);
  }

  buildContext(
    useAdditionalInstructions: boolean,
    useCharacterList: boolean,
    useSynopsis: boolean,
    useSummary: boolean
  ): any {
    const context: any = {};
    if (useAdditionalInstructions && this.additionalInstructions) {
      context.additional_instructions = this.additionalInstructions;
    }
    if (useCharacterList && this.characterList) context.character_list = this.characterList;
    if (useSynopsis && this.synopsis) context.synopsis = this.synopsis;
    if (useSummary && this.summary) context.summary = this.summary;
    return context;
  }

  translateLine(): void {
    if (!this.lineTextToTranslate || this.isTranslatingLine || this.stateService.hasActiveTask()) return;

    this.isTranslatingLine = true;
    this.lineTranslationResult = '';
    this.stateService.setTaskState(TASK_TYPES.translateLine, {
      status: 'processing',
      result: null,
      message: null,
      progress: this.defaultProgress(TASK_TYPES.translateLine),
      isPolling: true,
    });

    const context = this.buildContext(
      this.lineUseAdditionalInstructions,
      this.lineUseCharacterList,
      this.lineUseSynopsis,
      this.lineUseSummary
    );

    this.apiService.translateLine(
      this.lineTextToTranslate,
      context,
      this.lineInputLanguage,
      this.lineOutputLanguage
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          this.startLinePolling();
        } else {
          const errorMessage = response.message || 'Failed to start translation.';
          this.stateService.setTaskState(TASK_TYPES.translateLine, {
            status: 'error',
            message: errorMessage,
            isPolling: false,
          });
          this.showTaskError(TASK_TYPES.translateLine, errorMessage);
          this.isTranslatingLine = false;
        }
      },
      error: (error: any) => {
        console.error('Translation request failed:', error);
        this.errorDialogService.show('Failed to start translation. Please try again.');
        this.stateService.setTaskState(TASK_TYPES.translateLine, {
          status: 'error',
          message: 'Failed to start translation. Please try again.',
          isPolling: false,
        });
        this.isTranslatingLine = false;
      }
    });
  }

  private startLinePolling(): void {
    if (this.linePollingInterval) {
      return;
    }
    this.linePollingInterval = setInterval(() => {
      this.apiService.getTaskResult(TASK_TYPES.translateLine).subscribe({
        next: (response: TaskResultResponse) => {
          const taskData = response.data;
          this.stateService.setTaskState(TASK_TYPES.translateLine, {
            status: response.status,
            result: taskData?.result ?? null,
            message: response.message ?? null,
            progress: taskData?.progress ?? this.getExistingProgress(TASK_TYPES.translateLine),
            isPolling: response.status === 'processing',
          });
          if (response.status === 'complete' && taskData?.result) {
            this.lineTranslationResult = taskData.result.text ?? '';
            this.isTranslatingLine = false;
            this.stopLinePolling();
          } else if (response.status === 'error') {
            console.error('Translation error:', response.message);
            this.showTaskError(TASK_TYPES.translateLine, response.message || 'Translation failed.');
            this.isTranslatingLine = false;
            this.stopLinePolling();
          } else if (response.status === 'idle') {
            this.isTranslatingLine = false;
            this.stopLinePolling();
          }
        },
        error: (error: any) => {
          console.error('Polling error:', error);
          this.isTranslatingLine = false;
          this.stopLinePolling();
        }
      });
    }, 1000);
  }

  private stopLinePolling(): void {
    if (this.linePollingInterval) {
      clearInterval(this.linePollingInterval);
      this.linePollingInterval = undefined;
    }
  }

  translateFile(): void {
    if (!this.fileToTranslate || this.isTranslatingFile || this.stateService.hasActiveTask()) return;

    this.isTranslatingFile = true;
    this.stateService.setTaskState(TASK_TYPES.translateFile, {
      status: 'processing',
      result: null,
      message: null,
      progress: this.defaultProgress(TASK_TYPES.translateFile),
      isPolling: true,
    });

    const context = this.buildContext(
      this.fileUseAdditionalInstructions,
      this.fileUseCharacterList,
      this.fileUseSynopsis,
      this.fileUseSummary
    );

    this.apiService.translateFile(
      this.fileToTranslate,
      context,
      this.fileInputLanguage,
      this.fileOutputLanguage,
      this.batchSize
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          this.startFilePolling();
        } else {
          const errorMessage = response.message || 'Failed to start file translation.';
          this.stateService.setTaskState(TASK_TYPES.translateFile, {
            status: 'error',
            message: errorMessage,
            isPolling: false,
          });
          this.showTaskError(TASK_TYPES.translateFile, errorMessage);
          this.isTranslatingFile = false;
        }
      },
      error: (error: any) => {
        console.error('File translation request failed:', error);
        this.errorDialogService.show('Failed to start file translation. Please try again.');
        this.stateService.setTaskState(TASK_TYPES.translateFile, {
          status: 'error',
          message: 'Failed to start file translation. Please try again.',
          isPolling: false,
        });
        this.isTranslatingFile = false;
      }
    });
  }

  private startFilePolling(): void {
    if (this.filePollingInterval) {
      return;
    }
    this.filePollingInterval = setInterval(() => {
      this.apiService.getTaskResult(TASK_TYPES.translateFile).subscribe({
        next: (response: TaskResultResponse) => {
          const taskData = response.data;
          this.stateService.setTaskState(TASK_TYPES.translateFile, {
            status: response.status,
            result: taskData?.result ?? null,
            message: response.message ?? null,
            progress: taskData?.progress ?? this.getExistingProgress(TASK_TYPES.translateFile),
            isPolling: response.status === 'processing',
          });
          if (response.status === 'complete') {
            this.isTranslatingFile = false;
            this.stopFilePolling();
            this.refreshDownloads();
          } else if (response.status === 'error') {
            console.error('File translation error:', response.message);
            this.showTaskError(TASK_TYPES.translateFile, response.message || 'File translation failed.');
            this.isTranslatingFile = false;
            this.stopFilePolling();
          } else if (response.status === 'idle') {
            this.isTranslatingFile = false;
            this.stopFilePolling();
          }
        },
        error: (error: any) => {
          console.error('Polling error:', error);
          this.isTranslatingFile = false;
          this.stopFilePolling();
        }
      });
    }, 1000);
  }

  private stopFilePolling(): void {
    if (this.filePollingInterval) {
      clearInterval(this.filePollingInterval);
      this.filePollingInterval = undefined;
    }
  }

  reviewTranslatedFile(): void {
    if (!this.fileToTranslate || !this.translatedFileToReview || this.isReviewingTranslatedFile || this.stateService.hasActiveTask()) return;

    this.isReviewingTranslatedFile = true;
    this.stateService.setTaskState(TASK_TYPES.reviewTranslatedFile, {
      status: 'processing',
      result: null,
      message: null,
      progress: this.defaultProgress(TASK_TYPES.reviewTranslatedFile),
      isPolling: true,
    });

    const context = this.buildContext(
      this.fileUseAdditionalInstructions,
      this.fileUseCharacterList,
      this.fileUseSynopsis,
      this.fileUseSummary
    );

    this.apiService.reviewTranslatedFile(
      this.fileToTranslate,
      this.translatedFileToReview,
      context,
      this.fileInputLanguage,
      this.fileOutputLanguage,
      this.batchSize
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          this.startReviewPolling();
        } else {
          const errorMessage = response.message || 'Failed to start translation review.';
          this.stateService.setTaskState(TASK_TYPES.reviewTranslatedFile, {
            status: 'error',
            message: errorMessage,
            isPolling: false,
          });
          this.showTaskError(TASK_TYPES.reviewTranslatedFile, errorMessage);
          this.isReviewingTranslatedFile = false;
        }
      },
      error: (error: any) => {
        console.error('Translation review request failed:', error);
        this.errorDialogService.show('Failed to start translation review. Please try again.');
        this.stateService.setTaskState(TASK_TYPES.reviewTranslatedFile, {
          status: 'error',
          message: 'Failed to start translation review. Please try again.',
          isPolling: false,
        });
        this.isReviewingTranslatedFile = false;
      }
    });
  }

  private startReviewPolling(): void {
    if (this.reviewPollingInterval) {
      return;
    }
    this.reviewPollingInterval = setInterval(() => {
      this.apiService.getTaskResult(TASK_TYPES.reviewTranslatedFile).subscribe({
        next: (response: TaskResultResponse) => {
          const taskData = response.data;
          this.stateService.setTaskState(TASK_TYPES.reviewTranslatedFile, {
            status: response.status,
            result: taskData?.result ?? null,
            message: response.message ?? null,
            progress: taskData?.progress ?? this.getExistingProgress(TASK_TYPES.reviewTranslatedFile),
            isPolling: response.status === 'processing',
          });
          if (response.status === 'complete') {
            this.isReviewingTranslatedFile = false;
            this.stopReviewPolling();
            this.refreshDownloads();
          } else if (response.status === 'error') {
            console.error('Translation review error:', response.message);
            this.showTaskError(TASK_TYPES.reviewTranslatedFile, response.message || 'Translation review failed.');
            this.isReviewingTranslatedFile = false;
            this.stopReviewPolling();
          } else if (response.status === 'idle') {
            this.isReviewingTranslatedFile = false;
            this.stopReviewPolling();
          }
        },
        error: (error: any) => {
          console.error('Polling error:', error);
          this.isReviewingTranslatedFile = false;
          this.stopReviewPolling();
        }
      });
    }, 1000);
  }

  private stopReviewPolling(): void {
    if (this.reviewPollingInterval) {
      clearInterval(this.reviewPollingInterval);
      this.reviewPollingInterval = undefined;
    }
  }

  isAnyTaskRunning(): boolean {
    return this.stateService.hasActiveTask();
  }

  refreshDownloads(): void {
    this.isFetchingDownloads = true;
    this.downloadError = '';
    this.apiService.listFiles('sub-files').subscribe({
      next: (response) => {
        if (response.status === 'success') {
          this.availableDownloads = response.data?.files || [];
        } else {
          this.availableDownloads = [];
          this.downloadError = 'Unable to load downloads.';
        }
        this.isFetchingDownloads = false;
      },
      error: (error: any) => {
        console.error('Failed to load downloads:', error);
        this.availableDownloads = [];
        this.downloadError = 'Failed to load downloads. Please try again.';
        this.isFetchingDownloads = false;
      }
    });
  }

  downloadTranslatedFile(filename: string): void {
    if (!filename) return;
    this.apiService.getFileBlob('sub-files', filename).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      error: (error: any) => {
        console.error('Failed to download file:', error);
        this.errorDialogService.show('Failed to download file. Please try again.');
      }
    });
  }

  async deleteTranslatedFile(filename: string): Promise<void> {
    if (!filename || this.deletingDownload) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Confirm Deletion',
      message: `Delete ${filename}? This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.deletingDownload = filename;
    this.apiService.deleteFile('sub-files', filename).subscribe({
      next: () => {
        this.availableDownloads = this.availableDownloads.filter(file => file.name !== filename);
        this.deletingDownload = '';
      },
      error: (error: any) => {
        console.error('Failed to delete file:', error);
        this.errorDialogService.show('Failed to delete file. Please try again.');
        this.deletingDownload = '';
      }
    });
  }

  private defaultProgress(taskType: keyof typeof this.defaultTaskProgress): TaskProgress {
    return {
      task_type: taskType,
      ...this.defaultTaskProgress[taskType],
    };
  }

  private getExistingProgress(taskType: string): TaskProgress | null {
    return this.stateService.getTaskState(taskType).progress;
  }

  private showTaskError(taskType: string, message: string): void {
    if (this.lastShownTaskError[taskType] === message) {
      return;
    }
    this.lastShownTaskError[taskType] = message;
    this.errorDialogService.show(message);
  }

}
