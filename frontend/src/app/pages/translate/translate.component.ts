import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { ContextStatusComponent } from '../../components/context-status/context-status.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { ProgressBarComponent } from '../../components/progress-bar/progress-bar.component';
import { ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';

@Component({
  selector: 'app-translate',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, TextFieldComponent, FileUploadComponent, TooltipIconComponent, ContextStatusComponent, PrimaryButtonComponent, LoadingTextIndicatorComponent, ProgressBarComponent],
  templateUrl: './translate.component.html',
  styleUrl: './translate.component.scss'
})
export class TranslateComponent implements OnInit, OnDestroy {
  // Subsection collapsed states
  contextCollapsed = true;
  translateLineCollapsed = true;
  translateFileCollapsed = true;

  // Context data
  characterList = '';
  synopsis = '';
  summary = '';
  recap = '';
  activeContextTab: 'character' | 'synopsis' | 'summary' | 'recap' = 'character';

  // Translate Line
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
  fileUseCharacterList = false;
  fileUseSynopsis = false;
  fileUseSummary = false;
  fileUseRecap = false;
  fileInputLanguage = 'ja';
  fileOutputLanguage = 'en';
  batchSize = 3;
  fileToTranslate: File | null = null;
  fileTranslationResult = '';
  translatedFileName = '';
  isTranslatingFile = false;
  fileTranslationProgress = { current: 0, total: 0, avg_seconds_per_line: 0, eta_seconds: 0 };
  isFetchingFileInfo = false;
  fileInfoError = '';
  fileInfo: { totalLines: string; characterCount: string; averageCharacterCount: string } | null = null;
  private filePollingInterval?: any;

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
  ];

  constructor(
    private apiService: ApiService,
    private stateService: StateService
  ) {}

  ngOnInit(): void {
    this.loadContextFromState();
  }

  ngOnDestroy(): void {
    this.stopLinePolling();
    this.stopFilePolling();
  }

  loadContextFromState(): void {
    this.stateService.getState().subscribe((state: {
      characterList: string;
      synopsis: string;
      summary: string;
      recap: string;
    }) => {
      if (state.characterList) this.characterList = state.characterList;
      if (state.synopsis) this.synopsis = state.synopsis;
      if (state.summary) this.summary = state.summary;
      if (state.recap) this.recap = state.recap;
    });
  }

  setContextTab(tab: 'character' | 'synopsis' | 'summary' | 'recap'): void {
    this.activeContextTab = tab;
  }

  buildContext(useCharacterList: boolean, useSynopsis: boolean, useSummary: boolean, useRecap = false): any {
    const context: any = {};
    if (useCharacterList && this.characterList) context.character_list = this.characterList;
    if (useSynopsis && this.synopsis) context.synopsis = this.synopsis;
    if (useSummary && this.summary) context.summary = this.summary;
    if (useRecap && this.recap) context.recap = this.recap;
    return context;
  }

  translateLine(): void {
    if (!this.lineTextToTranslate || this.isTranslatingLine) return;

    this.isTranslatingLine = true;
    this.lineTranslationResult = '';

    const context = this.buildContext(
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
      next: (response: {status: string, message?: string}) => {
        if (response.status === 'processing') {
          this.startLinePolling();
        }
      },
      error: (error: any) => {
        console.error('Translation request failed:', error);
        alert('Failed to start translation. Please try again.');
        this.isTranslatingLine = false;
      }
    });
  }

  private startLinePolling(): void {
    this.linePollingInterval = setInterval(() => {
      this.apiService.getTranslationResult().subscribe({
        next: (response: {status: string, result?: {type: string, data: string}, message?: string}) => {
          if (response.status === 'complete' && response.result) {
            this.lineTranslationResult = response.result.data;
            this.isTranslatingLine = false;
            this.stopLinePolling();
          } else if (response.status === 'error') {
            console.error('Translation error:', response.message);
            alert('Translation failed: ' + (response.message || 'Unknown error'));
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

  onFileSelected(files: File[]): void {
    this.fileToTranslate = files.length > 0 ? files[0] : null;
    this.fileInfo = null;
    this.fileInfoError = '';

    if (this.fileToTranslate) {
      this.fetchFileInfo(this.fileToTranslate);
    }
  }

  private fetchFileInfo(file: File): void {
    this.isFetchingFileInfo = true;
    this.apiService.getTranscribeFileInfo(file).subscribe({
      next: (response: {status: string, result?: {total_lines: string, character_count: string, average_character_count: string}, message?: string}) => {
        if (response.status === 'success' && response.result) {
          this.fileInfo = {
            totalLines: response.result.total_lines,
            characterCount: response.result.character_count,
            averageCharacterCount: response.result.average_character_count
          };
          this.fileInfoError = '';
        } else {
          this.fileInfoError = response.message || 'Unable to analyze file.';
          this.fileInfo = null;
        }
        this.isFetchingFileInfo = false;
      },
      error: (error: any) => {
        console.error('Failed to get file info:', error);
        this.fileInfoError = 'Failed to fetch file info. Please try again.';
        this.fileInfo = null;
        this.isFetchingFileInfo = false;
      }
    });
  }

  translateFile(): void {
    if (!this.fileToTranslate || this.isTranslatingFile) return;

    this.isTranslatingFile = true;
    this.fileTranslationResult = '';
    this.fileTranslationProgress = { current: 0, total: 0, avg_seconds_per_line: 0, eta_seconds: 0 };

    const context = this.buildContext(
      this.fileUseCharacterList,
      this.fileUseSynopsis,
      this.fileUseSummary,
      this.fileUseRecap
    );

    this.apiService.translateFile(
      this.fileToTranslate,
      context,
      this.fileInputLanguage,
      this.fileOutputLanguage,
      this.batchSize
    ).subscribe({
      next: (response: {status: string, message?: string}) => {
        if (response.status === 'processing') {
          this.startFilePolling();
        }
      },
      error: (error: any) => {
        console.error('File translation request failed:', error);
        alert('Failed to start file translation. Please try again.');
        this.isTranslatingFile = false;
      }
    });
  }

  private startFilePolling(): void {
    this.filePollingInterval = setInterval(() => {
      this.apiService.getTranslationResult().subscribe({
        next: (response: {status: string, result?: {type: string, data: string, filename?: string}, message?: string, progress?: {current: number, total: number, avg_seconds_per_line: number, eta_seconds: number}}) => {
          if (response.status === 'translating' && response.progress) {
            this.fileTranslationProgress = response.progress;
            return;
          }
          if (response.status === 'complete' && response.result) {
            this.fileTranslationResult = response.result.data;
            this.translatedFileName = response.result.filename || 'translated.ass';
            this.isTranslatingFile = false;
            this.fileTranslationProgress = { current: 0, total: 0, avg_seconds_per_line: 0, eta_seconds: 0 };
            this.stopFilePolling();
          } else if (response.status === 'error') {
            console.error('File translation error:', response.message);
            alert('File translation failed: ' + (response.message || 'Unknown error'));
            this.isTranslatingFile = false;
            this.fileTranslationProgress = { current: 0, total: 0, avg_seconds_per_line: 0, eta_seconds: 0 };
            this.stopFilePolling();
          } else if (response.status === 'idle') {
            this.isTranslatingFile = false;
            this.fileTranslationProgress = { current: 0, total: 0, avg_seconds_per_line: 0, eta_seconds: 0 };
            this.stopFilePolling();
          }
        },
        error: (error: any) => {
          console.error('Polling error:', error);
          this.isTranslatingFile = false;
          this.fileTranslationProgress = { current: 0, total: 0, avg_seconds_per_line: 0, eta_seconds: 0 };
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

  downloadTranslatedFile(): void {
    if (!this.fileTranslationResult || !this.translatedFileName) return;

    // Create a blob from the file content
    const blob = new Blob([this.fileTranslationResult], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    
    // Create a temporary link element and trigger download
    const link = document.createElement('a');
    link.href = url;
    link.download = this.translatedFileName;
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }


}
