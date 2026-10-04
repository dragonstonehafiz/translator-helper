import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterOutlet, Router } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';
import { ProgressBarComponent } from './components/progress-bar/progress-bar.component';
import { ConfirmDialogComponent } from './components/confirm-dialog/confirm-dialog.component';
import { ErrorDialogComponent } from './components/error-dialog/error-dialog.component';
import { ApiService } from './services/api.service';
import { StateService } from './services/state.service';
import { WORKFLOW_TYPES, WorkflowId, WorkflowState } from './shared/workflow-types';
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

    <div class="progress-overlay" *ngIf="activeWorkflow as active">
      <div class="progress-overlay-card">
        <app-progress-bar
          [taskLabel]="workflowLabels[active.workflow]"
          [current]="active.current"
          [total]="active.total"
          [statusText]="active.message"
          [etaSeconds]="active.etaSeconds">
        </app-progress-bar>
      </div>
    </div>
  `,
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'Translator Helper';
  readonly workflowLabels: Record<WorkflowId, string> = {
    [WORKFLOW_TYPES.translateFile]: 'File Translation',
    [WORKFLOW_TYPES.reviewTranslatedFile]: 'Translation Review',
    [WORKFLOW_TYPES.translateLine]: 'Line Translation',
    [WORKFLOW_TYPES.transcribeFile]: 'File Transcription',
    [WORKFLOW_TYPES.transcribeClip]: 'Line Transcription',
    [WORKFLOW_TYPES.updateLibrary]: 'Library Update',
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

  get activeWorkflow(): WorkflowState | null {
    return this.stateService.getActiveWorkflow();
  }

  private checkBackendReady(): void {
    this.apiService.getServerVariables().subscribe({
      next: (response) => {
        const data = response.data;
        if (!data) {
          this.stateService.setReady(false);
          this.router.navigate(['/settings']);
          return;
        }
        this.stateService.setLlmReady(data.llm_ready);
        this.stateService.setAudioReady(data.audio_ready);
        this.stateService.setSearchReady(data.search_ready ?? null);
        this.stateService.setReady(data.llm_ready && data.audio_ready);
        if (!(data.llm_ready && data.audio_ready)) {
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
