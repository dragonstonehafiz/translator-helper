import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable, Subscription } from 'rxjs';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { DownloadsListComponent } from '../../components/downloads-list/downloads-list.component';
import { ApiResponse, ApiService, SeriesSummary } from '../../services/api.service';
import { StateService } from '../../services/state.service';
import { ConfirmationService } from '../../services/confirmation.service';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TabsComponent } from '../../components/tabs/tabs.component';
import { TabComponent } from '../../components/tabs/tab.component';
import { LANGUAGE_OPTIONS } from '../../shared/language-options';
import { ErrorDialogService } from '../../services/error-dialog.service';
import {
  WORKFLOW_TYPES,
  WorkflowId,
  WorkflowStartData,
  WorkflowState,
  WorkflowStatus,
  isTextResult,
} from '../../shared/workflow-types';

interface DownloadSection {
  folder: string;
  title: string;
  tooltip: string;
  files: { name: string; size: number; modified: string }[];
  isLoading: boolean;
  error: string;
  deletingFilename: string;
}

const PAGE_WORKFLOWS: WorkflowId[] = [
  WORKFLOW_TYPES.translateLine,
  WORKFLOW_TYPES.translateFile,
  WORKFLOW_TYPES.reviewTranslatedFile,
];

@Component({
  selector: 'app-translate',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, TextFieldComponent, TooltipIconComponent, PrimaryButtonComponent, LoadingTextIndicatorComponent, DownloadsListComponent, FileUploadComponent, TabsComponent, TabComponent],
  templateUrl: './translate.component.html',
  styleUrl: './translate.component.scss'
})
export class TranslateComponent implements OnInit, OnDestroy {
  // Series library
  seriesList: SeriesSummary[] = [];
  selectedSeriesId: string | null = null;

  // Translate Line
  lineInputLanguage = 'ja';
  lineOutputLanguage = 'en';
  lineTextToTranslate = '';
  lineTranslationResult = '';

  // Translate File
  fileInputLanguage = 'ja';
  fileOutputLanguage = 'en';
  batchSize = 50;
  fileToTranslate: File | null = null;
  translatedFileToReview: File | null = null;
  downloadSections: DownloadSection[] = [
    { folder: 'translated', title: 'Translated Files', tooltip: 'Subtitle files produced by file translation', files: [], isLoading: false, error: '', deletingFilename: '' },
    { folder: 'reviewed', title: 'Reviewed Files', tooltip: 'Corrected subtitle files produced by translation review', files: [], isLoading: false, error: '', deletingFilename: '' },
  ];

  /** Workflow whose start request is in flight, before the backend has accepted it. */
  private startingWorkflow: WorkflowId | null = null;
  private lastStatuses: Partial<Record<WorkflowId, WorkflowStatus>> = {};
  private workflowSubscription?: Subscription;
  private subtitleFileSubscription?: Subscription;
  private translatedSubtitleFileSubscription?: Subscription;
  private selectedSeriesSubscription?: Subscription;

  languageOptions = LANGUAGE_OPTIONS;

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
    private confirmationService: ConfirmationService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.selectedSeriesId = this.stateService.getSelectedSeriesId();
    this.selectedSeriesSubscription = this.stateService.selectedSeriesId$.subscribe(id => {
      this.selectedSeriesId = id;
    });
    this.loadSeriesList();
    this.fileToTranslate = this.stateService.getActiveSubtitleFile();
    this.subtitleFileSubscription = this.stateService.activeSubtitleFile$.subscribe(file => {
      this.fileToTranslate = file;
    });
    this.translatedFileToReview = this.stateService.getActiveTranslatedSubtitleFile();
    this.translatedSubtitleFileSubscription = this.stateService.activeTranslatedSubtitleFile$.subscribe(file => {
      this.translatedFileToReview = file;
    });

    const lineState = this.stateService.getWorkflowState(WORKFLOW_TYPES.translateLine);
    this.lineTranslationResult = isTextResult(lineState.result) ? lineState.result.text : '';
    for (const workflow of PAGE_WORKFLOWS) {
      this.lastStatuses[workflow] = this.stateService.getWorkflowState(workflow).status;
    }
    this.workflowSubscription = this.stateService.workflowStates$.subscribe(states => {
      for (const workflow of PAGE_WORKFLOWS) {
        const state = states[workflow];
        if (state) this.onWorkflowState(state);
      }
    });
    this.refreshDownloads();
  }

  ngOnDestroy(): void {
    this.workflowSubscription?.unsubscribe();
    this.subtitleFileSubscription?.unsubscribe();
    this.translatedSubtitleFileSubscription?.unsubscribe();
    this.selectedSeriesSubscription?.unsubscribe();
  }

  get isTranslatingLine(): boolean {
    return this.isBusy(WORKFLOW_TYPES.translateLine);
  }

  get isTranslatingFile(): boolean {
    return this.isBusy(WORKFLOW_TYPES.translateFile);
  }

  get isReviewingTranslatedFile(): boolean {
    return this.isBusy(WORKFLOW_TYPES.reviewTranslatedFile);
  }

  isAnyTaskRunning(): boolean {
    return this.startingWorkflow !== null || this.stateService.hasActiveWorkflow();
  }

  onSubtitleFileSelected(files: File[]): void {
    this.stateService.setActiveSubtitleFile(files[0] ?? null);
  }

  clearSubtitleFile(): void {
    this.stateService.setActiveSubtitleFile(null);
  }

  onTranslatedSubtitleFileSelected(files: File[]): void {
    this.stateService.setActiveTranslatedSubtitleFile(files[0] ?? null);
  }

  clearTranslatedSubtitleFile(): void {
    this.stateService.setActiveTranslatedSubtitleFile(null);
  }

  onSeriesSelected(seriesId: string): void {
    this.selectedSeriesId = seriesId || null;
    this.stateService.setSelectedSeriesId(this.selectedSeriesId);
  }

  private loadSeriesList(): void {
    this.apiService.listSeries().subscribe({
      next: (response) => {
        this.seriesList = response.data?.series ?? [];
      },
      error: () => this.errorDialogService.show('Failed to load series list.')
    });
  }

  translateLine(): void {
    if (!this.lineTextToTranslate || this.isAnyTaskRunning()) return;
    this.lineTranslationResult = '';
    this.startWorkflow(
      WORKFLOW_TYPES.translateLine,
      'Translating the entered text',
      this.apiService.translateLine(this.lineTextToTranslate, {}, this.lineInputLanguage, this.lineOutputLanguage),
      'Failed to start translation.',
    );
  }

  translateFile(): void {
    if (!this.fileToTranslate || this.isAnyTaskRunning()) return;
    this.startWorkflow(
      WORKFLOW_TYPES.translateFile,
      'Preparing subtitle file translation',
      this.apiService.translateFile(this.fileToTranslate, this.selectedSeriesId ?? '', this.fileInputLanguage, this.fileOutputLanguage, this.batchSize),
      'Failed to start file translation.',
    );
  }

  reviewTranslatedFile(): void {
    if (!this.fileToTranslate || !this.translatedFileToReview || this.isAnyTaskRunning()) return;
    this.startWorkflow(
      WORKFLOW_TYPES.reviewTranslatedFile,
      'Preparing translation review',
      this.apiService.reviewTranslatedFile(this.fileToTranslate, this.translatedFileToReview, this.selectedSeriesId ?? '', this.fileInputLanguage, this.fileOutputLanguage, this.batchSize),
      'Failed to start translation review.',
    );
  }

  /** Send a start request; once the backend accepts it, StateService polls the returned workflow. */
  private startWorkflow(workflow: WorkflowId, message: string, request: Observable<ApiResponse<WorkflowStartData>>, failure: string): void {
    this.startingWorkflow = workflow;
    request.subscribe({
      next: (response) => {
        this.startingWorkflow = null;
        if (response.status === 'processing' && response.data) {
          this.stateService.trackWorkflow(response.data.workflow, message);
        } else {
          this.errorDialogService.show(response.message || failure);
        }
      },
      error: (error: unknown) => {
        console.error(failure, error);
        this.startingWorkflow = null;
        this.errorDialogService.show(`${failure} Please try again.`);
      }
    });
  }

  /** React when one of this page's workflows finishes: show line results and refresh file lists. */
  private onWorkflowState(state: WorkflowState): void {
    const previous = this.lastStatuses[state.workflow];
    this.lastStatuses[state.workflow] = state.status;
    if (previous === state.status || state.status !== 'complete') return;

    if (state.workflow === WORKFLOW_TYPES.translateLine && isTextResult(state.result)) {
      this.lineTranslationResult = state.result.text;
    } else {
      this.refreshDownloads();
    }
  }

  private isBusy(workflow: WorkflowId): boolean {
    return this.startingWorkflow === workflow || this.stateService.getWorkflowState(workflow).status === 'processing';
  }

  refreshDownloads(): void {
    this.downloadSections.forEach(section => this.refreshDownloadSection(section));
  }

  refreshDownloadSection(section: DownloadSection): void {
    section.isLoading = true;
    section.error = '';
    this.apiService.listFiles(section.folder).subscribe({
      next: (response) => {
        if (response.status === 'success') {
          section.files = response.data?.files || [];
        } else {
          section.files = [];
          section.error = 'Unable to load downloads.';
        }
        section.isLoading = false;
      },
      error: (error: any) => {
        console.error(`Failed to load downloads for ${section.folder}:`, error);
        section.files = [];
        section.error = 'Failed to load downloads. Please try again.';
        section.isLoading = false;
      }
    });
  }

  downloadFile(section: DownloadSection, filename: string): void {
    if (!filename) return;
    this.apiService.getFileBlob(section.folder, filename).subscribe({
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

  async deleteFile(section: DownloadSection, filename: string): Promise<void> {
    if (!filename || section.deletingFilename) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Confirm Deletion',
      message: `Delete ${filename}? This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    section.deletingFilename = filename;
    this.apiService.deleteFile(section.folder, filename).subscribe({
      next: () => {
        section.files = section.files.filter(file => file.name !== filename);
        section.deletingFilename = '';
      },
      error: (error: any) => {
        console.error('Failed to delete file:', error);
        this.errorDialogService.show('Failed to delete file. Please try again.');
        section.deletingFilename = '';
      }
    });
  }
}
