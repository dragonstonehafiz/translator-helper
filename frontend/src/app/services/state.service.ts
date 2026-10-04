import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subscription, exhaustMap, timer } from 'rxjs';
import { ApiService } from './api.service';
import { ErrorDialogService } from './error-dialog.service';
import { WorkflowId, WorkflowState, WorkflowStatus } from '../shared/workflow-types';

export type SettingsFieldType = 'select' | 'text' | 'password' | 'number' | 'boolean';
export type SettingsValue = string | number | boolean;

export interface SettingsField {
  key: string;
  label: string;
  type: SettingsFieldType;
  value: SettingsValue;
  default: SettingsValue;
  required: boolean;
  is_set?: boolean;
  options?: {label: string; value: string}[];
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  help?: string;
}

export interface SettingsSchema {
  provider: string;
  title: string;
  fields: SettingsField[];
}

export interface SettingsSchemaBundle {
  audio: SettingsSchema | null;
  llm: SettingsSchema | null;
  search: SettingsSchema | null;
}

/** How often the active workflow is polled. */
const WORKFLOW_POLL_INTERVAL_MS = 1000;

export interface SubtitleFileInfo {
  totalLines: string;
  characterCount: string;
  averageCharacterCount: string;
}

@Injectable({
  providedIn: 'root'
})
export class StateService {
  private isReadySubject = new BehaviorSubject<boolean>(false);
  public isReady$: Observable<boolean> = this.isReadySubject.asObservable();
  private llmReadySubject = new BehaviorSubject<boolean | null>(null);
  public llmReady$: Observable<boolean | null> = this.llmReadySubject.asObservable();
  private audioReadySubject = new BehaviorSubject<boolean | null>(null);
  public audioReady$: Observable<boolean | null> = this.audioReadySubject.asObservable();
  private searchReadySubject = new BehaviorSubject<boolean | null>(null);
  public searchReady$: Observable<boolean | null> = this.searchReadySubject.asObservable();

  private serverAudioVarsSubject = new BehaviorSubject<Array<{ key?: string; label?: string; value?: unknown }> | null>(null);
  public serverAudioVars$: Observable<Array<{ key?: string; label?: string; value?: unknown }> | null> = this.serverAudioVarsSubject.asObservable();
  private serverLlmVarsSubject = new BehaviorSubject<Array<{ key?: string; label?: string; value?: unknown }> | null>(null);
  public serverLlmVars$: Observable<Array<{ key?: string; label?: string; value?: unknown }> | null> = this.serverLlmVarsSubject.asObservable();

  private loadingAudioSubject = new BehaviorSubject<boolean>(false);
  public loadingAudio$: Observable<boolean> = this.loadingAudioSubject.asObservable();

  private loadingLlmSubject = new BehaviorSubject<boolean>(false);
  public loadingLlm$: Observable<boolean> = this.loadingLlmSubject.asObservable();

  private selectedSeriesIdSubject = new BehaviorSubject<string | null>(null);
  public selectedSeriesId$: Observable<string | null> = this.selectedSeriesIdSubject.asObservable();

  private activeSubtitleFileSubject = new BehaviorSubject<File | null>(null);
  public activeSubtitleFile$: Observable<File | null> = this.activeSubtitleFileSubject.asObservable();

  private activeTranslatedSubtitleFileSubject = new BehaviorSubject<File | null>(null);
  public activeTranslatedSubtitleFile$: Observable<File | null> = this.activeTranslatedSubtitleFileSubject.asObservable();

  private subtitleFileInfoSubject = new BehaviorSubject<SubtitleFileInfo | null>(null);
  public subtitleFileInfo$: Observable<SubtitleFileInfo | null> = this.subtitleFileInfoSubject.asObservable();

  private subtitleFileInfoLoadingSubject = new BehaviorSubject<boolean>(false);
  public subtitleFileInfoLoading$: Observable<boolean> = this.subtitleFileInfoLoadingSubject.asObservable();

  private subtitleFileInfoErrorSubject = new BehaviorSubject<string>('');
  public subtitleFileInfoError$: Observable<string> = this.subtitleFileInfoErrorSubject.asObservable();

  private translatedSubtitleFileInfoSubject = new BehaviorSubject<SubtitleFileInfo | null>(null);
  public translatedSubtitleFileInfo$: Observable<SubtitleFileInfo | null> = this.translatedSubtitleFileInfoSubject.asObservable();

  private translatedSubtitleFileInfoLoadingSubject = new BehaviorSubject<boolean>(false);
  public translatedSubtitleFileInfoLoading$: Observable<boolean> = this.translatedSubtitleFileInfoLoadingSubject.asObservable();

  private translatedSubtitleFileInfoErrorSubject = new BehaviorSubject<string>('');
  public translatedSubtitleFileInfoError$: Observable<string> = this.translatedSubtitleFileInfoErrorSubject.asObservable();

  private workflowStatesSubject = new BehaviorSubject<Partial<Record<WorkflowId, WorkflowState>>>({});
  public workflowStates$: Observable<Partial<Record<WorkflowId, WorkflowState>>> = this.workflowStatesSubject.asObservable();
  private pollSubscription: Subscription | null = null;
  private pollGeneration = 0;

  private settingsSchemaSubject = new BehaviorSubject<SettingsSchemaBundle>({
    audio: null,
    llm: null,
    search: null,
  });
  public settingsSchema$: Observable<SettingsSchemaBundle> = this.settingsSchemaSubject.asObservable();

  constructor(
    private apiService: ApiService,
    private errorDialogService: ErrorDialogService,
  ) { }

  setReady(ready: boolean): void {
    this.isReadySubject.next(ready);
  }

  getReady(): boolean {
    return this.isReadySubject.value;
  }

  setLlmReady(ready: boolean | null): void {
    this.llmReadySubject.next(ready);
  }

  getLlmReady(): boolean | null {
    return this.llmReadySubject.value;
  }

  setAudioReady(ready: boolean | null): void {
    this.audioReadySubject.next(ready);
  }

  getAudioReady(): boolean | null {
    return this.audioReadySubject.value;
  }

  setSearchReady(ready: boolean | null): void {
    this.searchReadySubject.next(ready);
  }

  getSearchReady(): boolean | null {
    return this.searchReadySubject.value;
  }

  setServerVariables(variables: {
    audio: Array<{ key?: string; label?: string; value?: unknown }> | null;
    llm: Array<{ key?: string; label?: string; value?: unknown }> | null;
  }): void {
    this.serverAudioVarsSubject.next(variables.audio);
    this.serverLlmVarsSubject.next(variables.llm);
  }

  getServerVariables(): {
    audio: Array<{ key?: string; label?: string; value?: unknown }> | null;
    llm: Array<{ key?: string; label?: string; value?: unknown }> | null;
  } {
    return {
      audio: this.serverAudioVarsSubject.value,
      llm: this.serverLlmVarsSubject.value
    };
  }

  setLoadingAudio(loading: boolean): void {
    this.loadingAudioSubject.next(loading);
  }

  setLoadingLlm(loading: boolean): void {
    this.loadingLlmSubject.next(loading);
  }

  setSelectedSeriesId(seriesId: string | null): void {
    this.selectedSeriesIdSubject.next(seriesId);
  }

  getSelectedSeriesId(): string | null {
    return this.selectedSeriesIdSubject.value;
  }

  setActiveSubtitleFile(file: File | null): void {
    this.activeSubtitleFileSubject.next(file);
    this.setSubtitleFileInfo(null);
    this.setSubtitleFileInfoError('');
  }

  getActiveSubtitleFile(): File | null {
    return this.activeSubtitleFileSubject.value;
  }

  setActiveTranslatedSubtitleFile(file: File | null): void {
    this.activeTranslatedSubtitleFileSubject.next(file);
    this.setTranslatedSubtitleFileInfo(null);
    this.setTranslatedSubtitleFileInfoError('');
  }

  getActiveTranslatedSubtitleFile(): File | null {
    return this.activeTranslatedSubtitleFileSubject.value;
  }

  setSubtitleFileInfo(info: SubtitleFileInfo | null): void {
    this.subtitleFileInfoSubject.next(info);
  }

  getSubtitleFileInfo(): SubtitleFileInfo | null {
    return this.subtitleFileInfoSubject.value;
  }

  setSubtitleFileInfoLoading(isLoading: boolean): void {
    this.subtitleFileInfoLoadingSubject.next(isLoading);
  }

  getSubtitleFileInfoLoading(): boolean {
    return this.subtitleFileInfoLoadingSubject.value;
  }

  setSubtitleFileInfoError(error: string): void {
    this.subtitleFileInfoErrorSubject.next(error);
  }

  getSubtitleFileInfoError(): string {
    return this.subtitleFileInfoErrorSubject.value;
  }

  setTranslatedSubtitleFileInfo(info: SubtitleFileInfo | null): void {
    this.translatedSubtitleFileInfoSubject.next(info);
  }

  getTranslatedSubtitleFileInfo(): SubtitleFileInfo | null {
    return this.translatedSubtitleFileInfoSubject.value;
  }

  setTranslatedSubtitleFileInfoLoading(isLoading: boolean): void {
    this.translatedSubtitleFileInfoLoadingSubject.next(isLoading);
  }

  getTranslatedSubtitleFileInfoLoading(): boolean {
    return this.translatedSubtitleFileInfoLoadingSubject.value;
  }

  setTranslatedSubtitleFileInfoError(error: string): void {
    this.translatedSubtitleFileInfoErrorSubject.next(error);
  }

  getTranslatedSubtitleFileInfoError(): string {
    return this.translatedSubtitleFileInfoErrorSubject.value;
  }

  /**
   * Record that the backend accepted `workflow` and poll it until it completes, fails or goes idle.
   * Polling lives here, not in pages, so it keeps running across navigation; only one workflow runs at a time.
   */
  trackWorkflow(workflow: WorkflowId, message: string, seriesId: string | null = null): void {
    this.pollSubscription?.unsubscribe();
    const generation = ++this.pollGeneration;
    this.patchWorkflowState(workflow, {
      status: 'processing',
      activeTask: null,
      current: 0,
      total: 1,
      message,
      etaSeconds: 0,
      result: null,
      error: null,
      seriesId,
    });

    this.pollSubscription = timer(WORKFLOW_POLL_INTERVAL_MS, WORKFLOW_POLL_INTERVAL_MS).pipe(
      exhaustMap(() => this.apiService.getWorkflowResult(workflow)),
    ).subscribe({
      next: (response) => {
        if (generation !== this.pollGeneration) return;
        const data = response.data;
        const status = response.status as WorkflowStatus;
        const [current, total] = data?.progress ?? [0, 0];
        this.patchWorkflowState(workflow, {
          status,
          activeTask: data?.active_task ?? null,
          current,
          total,
          message: data?.message || this.getWorkflowState(workflow).message,
          etaSeconds: data?.eta_seconds ?? 0,
          result: data?.result ?? null,
          error: status === 'error' ? (response.message || 'The task failed.') : null,
        });
        if (status !== 'processing') {
          this.stopPolling();
          if (status === 'error') {
            this.errorDialogService.show(response.message || 'The task failed.');
          }
        }
      },
      error: (error: unknown) => {
        if (generation !== this.pollGeneration) return;
        console.error('Workflow polling failed:', error);
        const message = 'Lost contact with the backend while checking task progress.';
        this.patchWorkflowState(workflow, { status: 'error', error: message });
        this.stopPolling();
        this.errorDialogService.show(message);
      },
    });
  }

  getWorkflowState(workflow: WorkflowId): WorkflowState {
    return this.workflowStatesSubject.value[workflow] ?? this.createIdleWorkflowState(workflow);
  }

  getWorkflowStates(): Partial<Record<WorkflowId, WorkflowState>> {
    return this.workflowStatesSubject.value;
  }

  /** Return the workflow that is currently processing, if any. */
  getActiveWorkflow(): WorkflowState | null {
    return Object.values(this.workflowStatesSubject.value).find(state => state?.status === 'processing') ?? null;
  }

  hasActiveWorkflow(): boolean {
    return this.getActiveWorkflow() !== null;
  }

  private stopPolling(): void {
    this.pollSubscription?.unsubscribe();
    this.pollSubscription = null;
  }

  private patchWorkflowState(workflow: WorkflowId, patch: Partial<WorkflowState>): void {
    this.workflowStatesSubject.next({
      ...this.workflowStatesSubject.value,
      [workflow]: { ...this.getWorkflowState(workflow), ...patch, workflow },
    });
  }

  setSettingsSchema(schema: SettingsSchemaBundle): void {
    this.settingsSchemaSubject.next(schema);
  }

  getSettingsSchema(): SettingsSchemaBundle {
    return this.settingsSchemaSubject.value;
  }

  private createIdleWorkflowState(workflow: WorkflowId): WorkflowState {
    return {
      workflow,
      status: 'idle',
      activeTask: null,
      current: 0,
      total: 0,
      message: '',
      etaSeconds: 0,
      result: null,
      error: null,
      seriesId: null,
    };
  }
}
