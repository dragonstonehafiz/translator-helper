import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export type SettingsFieldType = 'select' | 'text' | 'password' | 'number' | 'boolean';
export type TaskStatus = 'idle' | 'processing' | 'complete' | 'error';

export interface SettingsField {
  key: string;
  label: string;
  type: SettingsFieldType;
  default?: string | number | boolean;
  required?: boolean;
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

export interface TaskProgress {
  task_type: string;
  current: number;
  total: number;
  status: string;
  eta_seconds: number;
}

export interface TaskResultPayload {
  text?: string;
}

export interface StoredTaskState {
  taskType: string;
  status: TaskStatus;
  result: TaskResultPayload | null;
  message: string | null;
  progress: TaskProgress | null;
  isPolling: boolean;
}

export interface SubtitleFileInfo {
  totalLines: string;
  characterCount: string;
  averageCharacterCount: string;
}

export const TASK_TYPES = {
  updateLibrary: 'TaskDeduplicateProposals',
  translateLine: 'TaskTranslateLine',
  translateFile: 'TaskTranslateFile',
  reviewTranslatedFile: 'TaskRetranslateReviewedLines',
  transcribeLine: 'TaskTranscribeLine',
  transcribeFile: 'TaskTranscribeFile',
} as const;

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

  private taskStatesSubject = new BehaviorSubject<Record<string, StoredTaskState>>({});
  public taskStates$: Observable<Record<string, StoredTaskState>> = this.taskStatesSubject.asObservable();

  private settingsSchemaSubject = new BehaviorSubject<SettingsSchemaBundle>({
    audio: null,
    llm: null,
    search: null,
  });
  public settingsSchema$: Observable<SettingsSchemaBundle> = this.settingsSchemaSubject.asObservable();

  constructor() { }

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

  setTaskState(taskType: string, patch: Partial<StoredTaskState>): StoredTaskState {
    const current = this.getTaskState(taskType);
    const next: StoredTaskState = {
      ...current,
      ...patch,
      taskType,
    };
    this.taskStatesSubject.next({
      ...this.taskStatesSubject.value,
      [taskType]: next,
    });
    return next;
  }

  getTaskState(taskType: string): StoredTaskState {
    return this.taskStatesSubject.value[taskType] ?? this.createIdleTaskState(taskType);
  }

  getTaskStates(): Record<string, StoredTaskState> {
    return this.taskStatesSubject.value;
  }

  clearTaskState(taskType: string): void {
    const next = { ...this.taskStatesSubject.value };
    delete next[taskType];
    this.taskStatesSubject.next(next);
  }

  hasActiveTask(taskTypes?: string[]): boolean {
    return Object.values(this.taskStatesSubject.value).some(task => {
      if (task.status !== 'processing') {
        return false;
      }
      return !taskTypes || taskTypes.includes(task.taskType);
    });
  }

  setSettingsSchema(schema: SettingsSchemaBundle): void {
    this.settingsSchemaSubject.next(schema);
  }

  getSettingsSchema(): SettingsSchemaBundle {
    return this.settingsSchemaSubject.value;
  }

  private createIdleTaskState(taskType: string): StoredTaskState {
    return {
      taskType,
      status: 'idle',
      result: null,
      message: null,
      progress: null,
      isPolling: false,
    };
  }
}
