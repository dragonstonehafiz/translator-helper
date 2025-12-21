import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../components/sidebar/sidebar.component';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';

@Component({
  selector: 'app-translate',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, SubsectionComponent, TextFieldComponent, FileUploadComponent],
  templateUrl: './translate.component.html',
  styleUrl: './translate.component.scss'
})
export class TranslateComponent implements OnInit, OnDestroy {
  // Subsection collapsed states
  contextCollapsed = false;
  translateLineCollapsed = false;
  translateFileCollapsed = false;

  // Context data
  webContext = '';
  characterList = '';
  synopsis = '';
  summary = '';
  recap = '';

  // Translate Line
  lineUseWebContext = false;
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
  fileUseWebContext = false;
  fileUseCharacterList = false;
  fileUseSynopsis = false;
  fileUseSummary = false;
  fileInputLanguage = 'ja';
  fileOutputLanguage = 'en';
  contextWindow = 3;
  fileToTranslate: File | null = null;
  fileTranslationResult = '';
  translatedFileName = '';
  isTranslatingFile = false;
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
      webContext: string;
      characterList: string;
      synopsis: string;
      summary: string;
      recap: string;
    }) => {
      if (state.webContext) this.webContext = state.webContext;
      if (state.characterList) this.characterList = state.characterList;
      if (state.synopsis) this.synopsis = state.synopsis;
      if (state.summary) this.summary = state.summary;
      if (state.recap) this.recap = state.recap;
    });
  }

  buildContext(useWebContext: boolean, useCharacterList: boolean, useSynopsis: boolean, useSummary: boolean): any {
    const context: any = {};
    if (useWebContext && this.webContext) context.web_context = this.webContext;
    if (useCharacterList && this.characterList) context.character_list = this.characterList;
    if (useSynopsis && this.synopsis) context.synopsis = this.synopsis;
    if (useSummary && this.summary) context.summary = this.summary;
    return context;
  }

  translateLine(): void {
    if (!this.lineTextToTranslate || this.isTranslatingLine) return;

    this.isTranslatingLine = true;
    this.lineTranslationResult = '';

    const context = this.buildContext(
      this.lineUseWebContext,
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
  }

  translateFile(): void {
    if (!this.fileToTranslate || this.isTranslatingFile) return;

    this.isTranslatingFile = true;
    this.fileTranslationResult = '';

    const context = this.buildContext(
      this.fileUseWebContext,
      this.fileUseCharacterList,
      this.fileUseSynopsis,
      this.fileUseSummary
    );

    this.apiService.translateFile(
      this.fileToTranslate,
      context,
      this.fileInputLanguage,
      this.fileOutputLanguage,
      this.contextWindow
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
        next: (response: {status: string, result?: {type: string, data: string, filename?: string}, message?: string}) => {
          if (response.status === 'complete' && response.result) {
            this.fileTranslationResult = response.result.data;
            this.translatedFileName = response.result.filename || 'translated.ass';
            this.isTranslatingFile = false;
            this.stopFilePolling();
          } else if (response.status === 'error') {
            console.error('File translation error:', response.message);
            alert('File translation failed: ' + (response.message || 'Unknown error'));
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
