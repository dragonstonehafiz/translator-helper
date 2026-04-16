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
  fileInfo: SubtitleFileInfo | null = null;
  isFetchingFileInfo = false;
  fileInfoError = '';

  private subscriptions = new Subscription();

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
    private confirmationService: ConfirmationService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.activeSubtitleFile = this.stateService.getActiveSubtitleFile();
    this.fileInfo = this.stateService.getSubtitleFileInfo();
    this.isFetchingFileInfo = this.stateService.getSubtitleFileInfoLoading();
    this.fileInfoError = this.stateService.getSubtitleFileInfoError();

    this.subscriptions.add(this.stateService.activeSubtitleFile$.subscribe(file => {
      this.activeSubtitleFile = file;
    }));
    this.subscriptions.add(this.stateService.subtitleFileInfo$.subscribe(info => {
      this.fileInfo = info;
    }));
    this.subscriptions.add(this.stateService.subtitleFileInfoLoading$.subscribe(isLoading => {
      this.isFetchingFileInfo = isLoading;
    }));
    this.subscriptions.add(this.stateService.subtitleFileInfoError$.subscribe(error => {
      this.fileInfoError = error;
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

  private fetchFileInfo(file: File): void {
    this.stateService.setSubtitleFileInfoLoading(true);
    this.apiService.getSubtitleFileInfo(file).subscribe({
      next: (response) => {
        if (response.status === 'success' && response.result) {
          this.stateService.setSubtitleFileInfo({
            totalLines: response.result.total_lines,
            characterCount: response.result.character_count,
            averageCharacterCount: response.result.average_character_count,
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

}
