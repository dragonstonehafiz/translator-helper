import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StateService } from '../../services/state.service';
import { ApiService } from '../../services/api.service';
import { Subscription, interval } from 'rxjs';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { ContextStatusComponent } from '../../components/context-status/context-status.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';

@Component({
  selector: 'app-context',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, FileUploadComponent, TextFieldComponent, TooltipIconComponent, ContextStatusComponent, LoadingTextIndicatorComponent, PrimaryButtonComponent],
  templateUrl: './context.component.html',
  styleUrl: './context.component.scss'
})
export class ContextComponent implements OnInit, OnDestroy {
  characterList = '';
  synopsis = '';
  summary = '';
  selectedFile: File | null = null;
  importFile: File | null = null;
  inputLanguage = 'ja';
  outputLanguage = 'en';
  runningLlm = false;
  private pollingSubscription?: Subscription;
  
  // Font sizes for textareas
  characterListFontSize = 14;
  synopsisFontSize = 14;
  summaryFontSize = 14;
  
  // View modes (true = read mode, false = edit mode)
  characterListReadMode = true;
  synopsisReadMode = true;
  summaryReadMode = true;
  
  // Context checkboxes for character list generation
  
  // Context checkboxes for synopsis generation
  synopsisUseCharacterList = true;
  
  // Context checkboxes for summary generation
  summaryUseCharacterList = true;

  isGeneratingCharacterList = false;
  isGeneratingSynopsis = false;
  isGeneratingSummary = false;
  isGeneratingRecap = false;

  // Collapsible section states
  importExportCollapsed = true;
  fileUploadCollapsed = true;
  contextCollapsed = true;
  recapCollapsed = true;

  activeContextTab: 'character' | 'synopsis' | 'summary' = 'character';
  
  // Recap section
  recap = '';
  recapFontSize = 14;
  recapReadMode = true;
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

    this.stateService.runningLlm$.subscribe(running => {
      this.runningLlm = running;
    });
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  startPolling(): void {
    if (this.pollingSubscription) {
      return;
    }
    this.pollingSubscription = interval(1000).subscribe(() => {
      this.apiService.checkRunning().subscribe({
        next: (status) => {
          const wasRunning = this.stateService.getRunningLlm();
          this.stateService.setRunningLlm(status.running_llm);
          
          // If context just finished running, check for result
          if (wasRunning && !status.running_llm) {
            this.checkContextResult();
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
  }

  checkContextResult(): void {
    this.apiService.getContextResult().subscribe({
      next: (response) => {
        if (response.status === 'success' && response.result) {
          if (response.result.type === 'character_list') {
            this.characterList = response.result.data;
            this.stateService.setCharacterList(response.result.data);
            this.isGeneratingCharacterList = false;
          } else if (response.result.type === 'synopsis') {
            this.synopsis = response.result.data;
            this.stateService.setSynopsis(response.result.data);
            this.isGeneratingSynopsis = false;
          } else if (response.result.type === 'summary') {
            this.summary = response.result.data;
            this.stateService.setSummary(response.result.data);
            this.isGeneratingSummary = false;
          } else if (response.result.type === 'recap') {
            this.recap = response.result.data;
            this.stateService.setRecap(response.result.data);
            this.isGeneratingRecap = false;
          }
        } else if (response.status === 'error') {
          alert(`Error: ${response.message}`);
          this.clearGenerationFlags();
        }
      },
      error: (err) => {
        console.error('Error checking context result:', err);
        this.clearGenerationFlags();
      }
    });
  }

  onSubtitleFilesSelected(files: File[]): void {
    if (files.length > 0) {
      const file = files[0];
      if (file.name.endsWith('.ass') || file.name.endsWith('.srt')) {
        this.selectedFile = file;
      } else {
        alert('Please select an .ass or .srt file.');
      }
    }
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

  adjustCharacterListFontSize(delta: number): void {
    this.characterListFontSize = Math.max(10, Math.min(24, this.characterListFontSize + delta));
  }

  adjustSynopsisFontSize(delta: number): void {
    this.synopsisFontSize = Math.max(10, Math.min(24, this.synopsisFontSize + delta));
  }

  adjustSummaryFontSize(delta: number): void {
    this.summaryFontSize = Math.max(10, Math.min(24, this.summaryFontSize + delta));
  }

  toggleCharacterListMode(): void {
    this.characterListReadMode = !this.characterListReadMode;
  }

  toggleSynopsisMode(): void {
    this.synopsisReadMode = !this.synopsisReadMode;
  }

  toggleSummaryMode(): void {
    this.summaryReadMode = !this.summaryReadMode;
  }

  setContextTab(tab: 'character' | 'synopsis' | 'summary'): void {
    this.activeContextTab = tab;
  }

  hasContent(value: string): boolean {
    return !!value && value.trim().length > 0;
  }

  hasAnyContextContent(): boolean {
    return this.hasContent(this.characterList) || this.hasContent(this.synopsis) || this.hasContent(this.summary);
  }

  generateCharacterList(): void {
    if (!this.selectedFile) {
      alert('Please upload a subtitle file first');
      return;
    }

    if (this.stateService.getRunningLlm()) {
      return;
    }

    this.isGeneratingCharacterList = true;

    // Build context dict with only checked and non-empty fields
    const context: any = {};
    
    this.apiService.generateCharacterList(
      this.selectedFile,
      context,
      this.inputLanguage,
      this.outputLanguage
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          console.log('Character list generation started, waiting for result...');
          this.startPolling();
        } else if (response.status === 'error') {
          alert(`Error: ${response.message}`);
          this.isGeneratingCharacterList = false;
        }
      },
      error: (err) => {
        console.error('Error generating character list:', err);
        alert('Failed to generate character list. Please try again.');
        this.isGeneratingCharacterList = false;
      }
    });
  }

  generateSynopsis(): void {
    if (!this.selectedFile) {
      alert('Please upload a subtitle file first');
      return;
    }

    if (this.stateService.getRunningLlm()) {
      return;
    }

    this.isGeneratingSynopsis = true;

    // Build context dict with only checked and non-empty fields
    const context: any = {};
    if (this.synopsisUseCharacterList && this.characterList.trim()) {
      context.character_list = this.characterList;
    }
    
    this.apiService.generateSynopsis(
      this.selectedFile,
      context,
      this.inputLanguage,
      this.outputLanguage
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          console.log('Synopsis generation started, waiting for result...');
          this.startPolling();
        } else if (response.status === 'error') {
          alert(`Error: ${response.message}`);
          this.isGeneratingSynopsis = false;
        }
      },
      error: (err) => {
        console.error('Error generating synopsis:', err);
        alert('Failed to generate synopsis. Please try again.');
        this.isGeneratingSynopsis = false;
      }
    });
  }

  generateSummary(): void {
    if (!this.selectedFile) {
      alert('Please upload a subtitle file first');
      return;
    }

    if (this.stateService.getRunningLlm()) {
      return;
    }

    this.isGeneratingSummary = true;

    // Build context dict with only checked and non-empty fields
    const context: any = {};
    if (this.summaryUseCharacterList && this.characterList.trim()) {
      context.character_list = this.characterList;
    }
    
    this.apiService.generateSummary(
      this.selectedFile,
      context,
      this.inputLanguage,
      this.outputLanguage
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          console.log('Summary generation started, waiting for result...');
          this.startPolling();
        } else if (response.status === 'error') {
          alert(`Error: ${response.message}`);
          this.isGeneratingSummary = false;
        }
      },
      error: (err) => {
        console.error('Error generating summary:', err);
        alert('Failed to generate summary. Please try again.');
        this.isGeneratingSummary = false;
      }
    });
  }

  exportContext(): void {
    const contextData = {
      inputLanguage: this.inputLanguage,
      outputLanguage: this.outputLanguage,
      characterList: this.characterList,
      synopsis: this.synopsis,
      summary: this.summary,
      recap: this.recap,
      exportDate: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(contextData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    // Use subtitle file name without extension, or default to generated-context
    let filename = 'generated-context.json';
    if (this.selectedFile) {
      const baseName = this.selectedFile.name.replace(/\.(ass|srt)$/i, '');
      filename = `${baseName}.json`;
    }
    
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  onImportFilesSelected(files: File[]): void {
    if (files.length > 0) {
      const file = files[0];
      if (file.name.endsWith('.json')) {
        this.importFile = file;
        this.processImportFile(file);
      } else {
        alert('Please select a JSON file.');
      }
    }
  }

  private processImportFile(file: File): void {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        
        // Load all fields from the imported data
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
        
        alert('Context imported successfully!');
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

    if (this.stateService.getRunningLlm()) {
      return;
    }

    this.isGeneratingRecap = true;

    this.apiService.generateRecap(
      this.recapContexts,
      this.inputLanguage,
      this.outputLanguage
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          console.log('Recap generation started');
          this.startPolling();
        } else if (response.status === 'error') {
          alert(response.message || 'Error generating recap');
          this.isGeneratingRecap = false;
        }
      },
      error: (error) => {
        console.error('Error:', error);
        alert('Failed to start recap generation');
        this.isGeneratingRecap = false;
      }
    });
  }

  private clearGenerationFlags(): void {
    this.isGeneratingCharacterList = false;
    this.isGeneratingSynopsis = false;
    this.isGeneratingSummary = false;
    this.isGeneratingRecap = false;
  }

  toggleRecapMode(): void {
    this.recapReadMode = !this.recapReadMode;
  }

  adjustRecapFontSize(change: number): void {
    this.recapFontSize = Math.max(10, Math.min(24, this.recapFontSize + change));
  }

  formatMarkdown(text: string): string {
    if (!text) return '';
    
    // Basic markdown formatting
    let html = text
      // Headers
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      // Bold
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Links
      .replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      // Line breaks
      .replace(/\n/g, '<br>');
    
    return html;
  }
}
