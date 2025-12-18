import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StateService } from '../../services/state.service';
import { ApiService } from '../../services/api.service';
import { Subscription, interval } from 'rxjs';
import { SidebarComponent } from '../../components/sidebar/sidebar.component';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';

@Component({
  selector: 'app-context',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, SubsectionComponent, FileUploadComponent],
  templateUrl: './context.component.html',
  styleUrl: './context.component.scss'
})
export class ContextComponent implements OnInit, OnDestroy {
  seriesName = '';
  keywords = '';
  characterList = '';
  summary = '';
  webContext = '';
  selectedFile: File | null = null;
  importFile: File | null = null;
  inputLanguage = 'ja';
  outputLanguage = 'en';
  runningContext = false;
  private pollingSubscription?: Subscription;
  
  // Font sizes for textareas
  webContextFontSize = 14;
  characterListFontSize = 14;
  summaryFontSize = 14;
  
  // View modes (true = read mode, false = edit mode)
  webContextReadMode = true;
  characterListReadMode = false;
  summaryReadMode = false;
  
  // Context checkboxes for character list generation
  characterListUseWebContext = true;
  characterListUseSummary = false;
  
  // Context checkboxes for summary generation
  summaryUseWebContext = true;
  summaryUseCharacterList = true;
  
  // Collapsible section states
  importExportCollapsed = false;
  fileUploadCollapsed = false;
  webContextCollapsed = false;
  contextCollapsed = false;
  recapCollapsed = false;
  
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
    this.webContext = this.stateService.getWebContext();
    this.characterList = this.stateService.getCharacterList();
    this.summary = this.stateService.getSummary();
    this.recap = this.stateService.getRecap();

    // Start polling for running status
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.pollingSubscription?.unsubscribe();
  }

  startPolling(): void {
    this.pollingSubscription = interval(500).subscribe(() => {
      this.apiService.checkRunning().subscribe({
        next: (status) => {
          const wasRunning = this.runningContext;
          this.runningContext = status.running_context;
          this.stateService.setRunningContext(status.running_context);
          
          // If context just finished running, check for result
          if (wasRunning && !status.running_context) {
            this.checkContextResult();
          }
        },
        error: (err) => console.error('Error checking running status:', err)
      });
    });
  }

  checkContextResult(): void {
    this.apiService.getContextResult().subscribe({
      next: (response) => {
        if (response.status === 'success' && response.result) {
          if (response.result.type === 'web_context') {
            this.webContext = response.result.data;
            this.stateService.setWebContext(response.result.data);
          } else if (response.result.type === 'character_list') {
            this.characterList = response.result.data;
            this.stateService.setCharacterList(response.result.data);
          } else if (response.result.type === 'summary') {
            this.summary = response.result.data;
            this.stateService.setSummary(response.result.data);
          } else if (response.result.type === 'recap') {
            this.recap = response.result.data;
            this.stateService.setRecap(response.result.data);
          }
        } else if (response.status === 'error') {
          alert(`Error: ${response.message}`);
        }
      },
      error: (err) => console.error('Error checking context result:', err)
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

  gatherWebContext(): void {
    if (!this.seriesName || !this.keywords) {
      alert('Please enter both series name and keywords');
      return;
    }

    if (this.runningContext) {
      return;
    }

    this.apiService.generateWebContext(
      this.seriesName,
      this.keywords,
      this.inputLanguage,
      this.outputLanguage
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          console.log('Web context generation started, waiting for result...');
          // Result will be picked up by polling
        } else if (response.status === 'error') {
          alert(`Error: ${response.message}`);
        }
      },
      error: (err) => {
        console.error('Error generating web context:', err);
        alert('Failed to generate web context. Please try again.');
      }
    });
  }

  // Save to state service whenever values change
  updateWebContext(): void {
    this.stateService.setWebContext(this.webContext);
  }

  updateCharacterList(): void {
    this.stateService.setCharacterList(this.characterList);
  }

  updateSummary(): void {
    this.stateService.setSummary(this.summary);
  }

  adjustWebContextFontSize(delta: number): void {
    this.webContextFontSize = Math.max(10, Math.min(24, this.webContextFontSize + delta));
  }

  adjustCharacterListFontSize(delta: number): void {
    this.characterListFontSize = Math.max(10, Math.min(24, this.characterListFontSize + delta));
  }

  adjustSummaryFontSize(delta: number): void {
    this.summaryFontSize = Math.max(10, Math.min(24, this.summaryFontSize + delta));
  }

  toggleWebContextMode(): void {
    this.webContextReadMode = !this.webContextReadMode;
  }

  toggleCharacterListMode(): void {
    this.characterListReadMode = !this.characterListReadMode;
  }

  toggleSummaryMode(): void {
    this.summaryReadMode = !this.summaryReadMode;
  }

  generateCharacterList(): void {
    if (!this.selectedFile) {
      alert('Please upload a subtitle file first');
      return;
    }

    if (this.runningContext) {
      return;
    }

    // Read file content (simplified - in production you'd want proper file reading)
    const reader = new FileReader();
    reader.onload = (e) => {
      const transcript = e.target?.result as string;
      
      // Build context dict with only checked and non-empty fields
      const context: any = {};
      if (this.characterListUseWebContext && this.webContext.trim()) {
        context.web_context = this.webContext;
      }
      if (this.characterListUseSummary && this.summary.trim()) {
        context.summary = this.summary;
      }
      
      this.apiService.generateCharacterList(
        transcript,
        context,
        this.inputLanguage,
        this.outputLanguage
      ).subscribe({
        next: (response) => {
          if (response.status === 'processing') {
            console.log('Character list generation started, waiting for result...');
          } else if (response.status === 'error') {
            alert(`Error: ${response.message}`);
          }
        },
        error: (err) => {
          console.error('Error generating character list:', err);
          alert('Failed to generate character list. Please try again.');
        }
      });
    };
    reader.readAsText(this.selectedFile);
  }

  generateSummary(): void {
    if (!this.selectedFile) {
      alert('Please upload a subtitle file first');
      return;
    }

    if (this.runningContext) {
      return;
    }

    // Read file content
    const reader = new FileReader();
    reader.onload = (e) => {
      const transcript = e.target?.result as string;
      
      // Build context dict with only checked and non-empty fields
      const context: any = {};
      if (this.summaryUseWebContext && this.webContext.trim()) {
        context.web_context = this.webContext;
      }
      if (this.summaryUseCharacterList && this.characterList.trim()) {
        context.character_list = this.characterList;
      }
      
      this.apiService.generateSummary(
        transcript,
        context,
        this.inputLanguage,
        this.outputLanguage
      ).subscribe({
        next: (response) => {
          if (response.status === 'processing') {
            console.log('Summary generation started, waiting for result...');
          } else if (response.status === 'error') {
            alert(`Error: ${response.message}`);
          }
        },
        error: (err) => {
          console.error('Error generating summary:', err);
          alert('Failed to generate summary. Please try again.');
        }
      });
    };
    reader.readAsText(this.selectedFile);
  }

  exportContext(): void {
    const contextData = {
      seriesName: this.seriesName,
      keywords: this.keywords,
      inputLanguage: this.inputLanguage,
      outputLanguage: this.outputLanguage,
      webContext: this.webContext,
      characterList: this.characterList,
      summary: this.summary,
      recap: this.recap,
      exportDate: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(contextData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `context-${this.seriesName || 'export'}-${Date.now()}.json`;
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
        if (data.seriesName !== undefined) this.seriesName = data.seriesName;
        if (data.keywords !== undefined) this.keywords = data.keywords;
        if (data.inputLanguage !== undefined) this.inputLanguage = data.inputLanguage;
        if (data.outputLanguage !== undefined) this.outputLanguage = data.outputLanguage;
        if (data.webContext !== undefined) {
          this.webContext = data.webContext;
          this.stateService.setWebContext(data.webContext);
        }
        if (data.characterList !== undefined) {
          this.characterList = data.characterList;
          this.stateService.setCharacterList(data.characterList);
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

    if (this.runningContext) {
      return;
    }

    this.apiService.generateRecap(
      this.recapContexts,
      this.inputLanguage,
      this.outputLanguage
    ).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          console.log('Recap generation started');
        } else if (response.status === 'error') {
          alert(response.message || 'Error generating recap');
        }
      },
      error: (error) => {
        console.error('Error:', error);
        alert('Failed to start recap generation');
      }
    });
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
