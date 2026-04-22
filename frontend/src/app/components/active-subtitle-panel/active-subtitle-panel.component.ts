import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { FileUploadComponent } from '../file-upload/file-upload.component';
import { SubsectionComponent } from '../subsection/subsection.component';
import { ApiService } from '../../services/api.service';
import { StateService, SubtitleFileInfo } from '../../services/state.service';
import { ConfirmationService } from '../../services/confirmation.service';
import { ErrorDialogService } from '../../services/error-dialog.service';

@Component({
  selector: 'app-active-subtitle-panel',
  standalone: true,
  imports: [CommonModule, FileUploadComponent, SubsectionComponent],
  templateUrl: './active-subtitle-panel.component.html',
  styleUrl: './active-subtitle-panel.component.scss'
})
export class ActiveSubtitlePanelComponent implements OnInit, OnDestroy {
  activeSubtitleFile: File | null = null;
  activeTranslatedSubtitleFile: File | null = null;
  fileInfo: SubtitleFileInfo | null = null;
  translatedFileInfo: SubtitleFileInfo | null = null;
  isFetchingFileInfo = false;
  isFetchingTranslatedFileInfo = false;
  fileInfoError = '';
  translatedFileInfoError = '';

  private subscriptions = new Subscription();

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
    private confirmationService: ConfirmationService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.activeSubtitleFile = this.stateService.getActiveSubtitleFile();
    this.activeTranslatedSubtitleFile = this.stateService.getActiveTranslatedSubtitleFile();
    this.fileInfo = this.stateService.getSubtitleFileInfo();
    this.translatedFileInfo = this.stateService.getTranslatedSubtitleFileInfo();
    this.isFetchingFileInfo = this.stateService.getSubtitleFileInfoLoading();
    this.isFetchingTranslatedFileInfo = this.stateService.getTranslatedSubtitleFileInfoLoading();
    this.fileInfoError = this.stateService.getSubtitleFileInfoError();
    this.translatedFileInfoError = this.stateService.getTranslatedSubtitleFileInfoError();

    this.subscriptions.add(this.stateService.activeSubtitleFile$.subscribe(file => {
      this.activeSubtitleFile = file;
    }));
    this.subscriptions.add(this.stateService.activeTranslatedSubtitleFile$.subscribe(file => {
      this.activeTranslatedSubtitleFile = file;
    }));
    this.subscriptions.add(this.stateService.subtitleFileInfo$.subscribe(info => {
      this.fileInfo = info;
    }));
    this.subscriptions.add(this.stateService.translatedSubtitleFileInfo$.subscribe(info => {
      this.translatedFileInfo = info;
    }));
    this.subscriptions.add(this.stateService.subtitleFileInfoLoading$.subscribe(isLoading => {
      this.isFetchingFileInfo = isLoading;
    }));
    this.subscriptions.add(this.stateService.translatedSubtitleFileInfoLoading$.subscribe(isLoading => {
      this.isFetchingTranslatedFileInfo = isLoading;
    }));
    this.subscriptions.add(this.stateService.subtitleFileInfoError$.subscribe(error => {
      this.fileInfoError = error;
    }));
    this.subscriptions.add(this.stateService.translatedSubtitleFileInfoError$.subscribe(error => {
      this.translatedFileInfoError = error;
    }));
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  onSubtitleFilesSelected(files: File[]): void {
    if (files.length === 0) return;
    const file = files[0];
    if (!file.name.match(/\.(ass|srt)$/i)) {
      this.errorDialogService.show('Please select an .ass or .srt file.');
      return;
    }

    this.stateService.setActiveSubtitleFile(file);
    this.fetchFileInfo(file);
  }

  onTranslatedSubtitleFilesSelected(files: File[]): void {
    if (files.length === 0) return;
    const file = files[0];
    if (!file.name.match(/\.(ass|srt)$/i)) {
      this.errorDialogService.show('Please select an .ass or .srt file.');
      return;
    }

    this.stateService.setActiveTranslatedSubtitleFile(file);
    this.fetchTranslatedFileInfo(file);
  }

  async clearSubtitleFile(): Promise<void> {
    if (!this.activeSubtitleFile) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Clear Subtitle File',
      message: `Clear "${this.activeSubtitleFile.name}" as the active subtitle file?`,
      confirmLabel: 'Clear',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.stateService.setActiveSubtitleFile(null);
    this.stateService.setSubtitleFileInfoLoading(false);
  }

  async clearTranslatedSubtitleFile(): Promise<void> {
    if (!this.activeTranslatedSubtitleFile) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Clear Translated File',
      message: `Clear "${this.activeTranslatedSubtitleFile.name}" as the active translated subtitle file?`,
      confirmLabel: 'Clear',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.stateService.setActiveTranslatedSubtitleFile(null);
    this.stateService.setTranslatedSubtitleFileInfoLoading(false);
  }

  private fetchFileInfo(file: File): void {
    this.stateService.setSubtitleFileInfoLoading(true);
    this.apiService.getSubtitleFileInfo(file).subscribe({
      next: (response) => {
        if (response.status === 'success' && response.data) {
          this.stateService.setSubtitleFileInfo({
            totalLines: response.data.total_lines,
            characterCount: response.data.character_count,
            averageCharacterCount: response.data.average_character_count,
          });
          this.stateService.setSubtitleFileInfoError('');
        } else {
          this.stateService.setSubtitleFileInfo(null);
          this.stateService.setSubtitleFileInfoError(response.message || 'Unable to analyze file.');
        }
        this.stateService.setSubtitleFileInfoLoading(false);
      },
      error: (error) => {
        console.error('Failed to get subtitle file info:', error);
        this.stateService.setSubtitleFileInfo(null);
        this.stateService.setSubtitleFileInfoError('Failed to fetch file info. Please try again.');
        this.stateService.setSubtitleFileInfoLoading(false);
      }
    });
  }

  private fetchTranslatedFileInfo(file: File): void {
    this.stateService.setTranslatedSubtitleFileInfoLoading(true);
    this.apiService.getSubtitleFileInfo(file).subscribe({
      next: (response) => {
        if (response.status === 'success' && response.data) {
          this.stateService.setTranslatedSubtitleFileInfo({
            totalLines: response.data.total_lines,
            characterCount: response.data.character_count,
            averageCharacterCount: response.data.average_character_count,
          });
          this.stateService.setTranslatedSubtitleFileInfoError('');
        } else {
          this.stateService.setTranslatedSubtitleFileInfo(null);
          this.stateService.setTranslatedSubtitleFileInfoError(response.message || 'Unable to analyze file.');
        }
        this.stateService.setTranslatedSubtitleFileInfoLoading(false);
      },
      error: (error) => {
        console.error('Failed to get translated subtitle file info:', error);
        this.stateService.setTranslatedSubtitleFileInfo(null);
        this.stateService.setTranslatedSubtitleFileInfoError('Failed to fetch file info. Please try again.');
        this.stateService.setTranslatedSubtitleFileInfoLoading(false);
      }
    });
  }

}
