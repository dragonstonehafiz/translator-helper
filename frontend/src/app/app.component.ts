import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterOutlet, Router } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';
import { ProgressBarComponent } from './components/progress-bar/progress-bar.component';
import { ConfirmDialogComponent } from './components/confirm-dialog/confirm-dialog.component';
import { ErrorDialogComponent } from './components/error-dialog/error-dialog.component';
import { ApiService } from './services/api.service';
import { StateService, TaskProgress, TASK_TYPES } from './services/state.service';
import { ConfirmationService } from './services/confirmation.service';
import { ErrorDialogService } from './services/error-dialog.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, NavbarComponent, ProgressBarComponent, ConfirmDialogComponent, ErrorDialogComponent],
  template: `
    <app-navbar></app-navbar>
    <router-outlet></router-outlet>

    <app-confirm-dialog
      *ngIf="confirmationService.dialog$ | async as dialog"
      [dialog]="dialog"
      (confirmed)="confirmationService.resolve(true)"
      (cancelled)="confirmationService.resolve(false)">
    </app-confirm-dialog>

    <app-error-dialog
      *ngIf="errorDialogService.dialog$ | async as dialog"
      [dialog]="dialog"
      (dismissed)="errorDialogService.dismiss()">
    </app-error-dialog>

    <div class="progress-overlay" *ngIf="activeProgress">
      <div class="progress-overlay-card">
        <app-progress-bar
          [taskLabel]="activeTaskLabel"
          [current]="activeProgress.current"
          [total]="activeProgress.total"
          [statusText]="activeProgress.status"
          [etaSeconds]="activeProgress.eta_seconds">
        </app-progress-bar>
      </div>
    </div>
  `,
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'Translator Helper';
  private readonly taskOrder = [
    TASK_TYPES.translateFile,
    TASK_TYPES.translateLine,
    TASK_TYPES.transcribeFile,
    TASK_TYPES.transcribeLine,
    TASK_TYPES.generateCharacterList,
    TASK_TYPES.generateSynopsis,
    TASK_TYPES.generateSummary,
    TASK_TYPES.generateRecap,
  ];
  private readonly taskLabels: Record<string, string> = {
    [TASK_TYPES.translateFile]: 'File Translation',
    [TASK_TYPES.translateLine]: 'Line Translation',
    [TASK_TYPES.transcribeFile]: 'File Transcription',
    [TASK_TYPES.transcribeLine]: 'Line Transcription',
    [TASK_TYPES.generateCharacterList]: 'Character List',
    [TASK_TYPES.generateSynopsis]: 'Synopsis',
    [TASK_TYPES.generateSummary]: 'Summary',
    [TASK_TYPES.generateRecap]: 'Recap',
  };

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
    private router: Router,
    readonly confirmationService: ConfirmationService,
    readonly errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.checkBackendReady();
  }

  get activeProgress(): TaskProgress | null {
    const taskStates = this.stateService.getTaskStates();

    for (const taskType of this.taskOrder) {
      const taskState = taskStates[taskType];
      if (taskState?.status === 'processing' && taskState.progress) {
        return taskState.progress;
      }
    }

    return null;
  }

  get activeTaskLabel(): string {
    const taskStates = this.stateService.getTaskStates();

    for (const taskType of this.taskOrder) {
      const taskState = taskStates[taskType];
      if (taskState?.status === 'processing' && taskState.progress) {
        return this.taskLabels[taskType] ?? 'Task In Progress';
      }
    }

    return 'Task In Progress';
  }

  private checkBackendReady(): void {
    this.apiService.getServerVariables().subscribe({
      next: (response) => {
        this.stateService.setLlmReady(response.llm_ready);
        this.stateService.setAudioReady(response.audio_ready);
        this.stateService.setReady(response.llm_ready && response.audio_ready);
        if (!(response.llm_ready && response.audio_ready)) {
          this.router.navigate(['/settings']);
        }
      },
      error: (error) => {
        console.error('Failed to check backend readiness:', error);
        this.stateService.setReady(false);
        this.router.navigate(['/settings']);
      }
    });
  }
}
