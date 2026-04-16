import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
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
}

export interface TaskProgress {
  task_type: string;
  current: number;
  total: number;
  status: string;
  eta_seconds: number;
}

export interface TaskResultPayload {
  type: string;
  data?: string;
  filename?: string;
}

export interface StoredTaskState {
  taskType: string;
  status: TaskStatus;
  result: TaskResultPayload | null;
  message: string | null;
  progress: TaskProgress | null;
  isPolling: boolean;
}

export interface AppContentState {
  characterList: string;
  synopsis: string;
  summary: string;
  recap: string;
  additionalInstructions: string;
}

export interface ContextFileData {
  characterList?: string;
  synopsis?: string;
  summary?: string;
  recap?: string;
  additionalInstructions?: string;
  inputLanguage?: string;
  outputLanguage?: string;
}

export interface SubtitleFileInfo {
  totalLines: string;
  characterCount: string;
  averageCharacterCount: string;
}

export const TASK_TYPES = {
  generateCharacterList: 'TaskGenerateCharacterList',
  generateSynopsis: 'TaskGenerateSynopsis',
  generateSummary: 'TaskGenerateSummary',
  generateRecap: 'TaskGenerateRecap',
  translateLine: 'TaskTranslateLine',
  translateFile: 'TaskTranslateFile',
  transcribeLine: 'TaskTranscribeLine',
  transcribeFile: 'TaskTranscribeFile',
} as const;

@Injectable({
  providedIn: 'root'
})
export class StateService {
  private readonly baseUrl = 'http://localhost:8000';
  private isReadySubject = new BehaviorSubject<boolean>(false);
  public isReady$: Observable<boolean> = this.isReadySubject.asObservable();
  private llmReadySubject = new BehaviorSubject<boolean | null>(null);
  public llmReady$: Observable<boolean | null> = this.llmReadySubject.asObservable();
  private audioReadySubject = new BehaviorSubject<boolean | null>(null);
  public audioReady$: Observable<boolean | null> = this.audioReadySubject.asObservable();

  private serverAudioVarsSubject = new BehaviorSubject<Array<{ key?: string; label?: string; value?: unknown }> | null>(null);
  public serverAudioVars$: Observable<Array<{ key?: string; label?: string; value?: unknown }> | null> = this.serverAudioVarsSubject.asObservable();
  private serverLlmVarsSubject = new BehaviorSubject<Array<{ key?: string; label?: string; value?: unknown }> | null>(null);
  public serverLlmVars$: Observable<Array<{ key?: string; label?: string; value?: unknown }> | null> = this.serverLlmVarsSubject.asObservable();

  private loadingAudioSubject = new BehaviorSubject<boolean>(false);
  public loadingAudio$: Observable<boolean> = this.loadingAudioSubject.asObservable();

  private loadingLlmSubject = new BehaviorSubject<boolean>(false);
  public loadingLlm$: Observable<boolean> = this.loadingLlmSubject.asObservable();

  private contentStateSubject = new BehaviorSubject<AppContentState>({
    characterList: '',
    synopsis: '',
    summary: '',
    recap: '',
    additionalInstructions: '',
  });
  public contentState$: Observable<AppContentState> = this.contentStateSubject.asObservable();

  private characterListSubject = new BehaviorSubject<string>('');
  public characterList$: Observable<string> = this.characterListSubject.asObservable();

  private summarySubject = new BehaviorSubject<string>('');
  public summary$: Observable<string> = this.summarySubject.asObservable();

  private synopsisSubject = new BehaviorSubject<string>('');
  public synopsis$: Observable<string> = this.synopsisSubject.asObservable();

  private recapSubject = new BehaviorSubject<string>('');
  public recap$: Observable<string> = this.recapSubject.asObservable();

  private additionalInstructionsSubject = new BehaviorSubject<string>('');
  public additionalInstructions$: Observable<string> = this.additionalInstructionsSubject.asObservable();

  private activeSubtitleFileSubject = new BehaviorSubject<File | null>(null);
  public activeSubtitleFile$: Observable<File | null> = this.activeSubtitleFileSubject.asObservable();

  private subtitleFileInfoSubject = new BehaviorSubject<SubtitleFileInfo | null>(null);
  public subtitleFileInfo$: Observable<SubtitleFileInfo | null> = this.subtitleFileInfoSubject.asObservable();

  private subtitleFileInfoLoadingSubject = new BehaviorSubject<boolean>(false);
  public subtitleFileInfoLoading$: Observable<boolean> = this.subtitleFileInfoLoadingSubject.asObservable();

  private subtitleFileInfoErrorSubject = new BehaviorSubject<string>('');
  public subtitleFileInfoError$: Observable<string> = this.subtitleFileInfoErrorSubject.asObservable();

  private taskStatesSubject = new BehaviorSubject<Record<string, StoredTaskState>>({});
  public taskStates$: Observable<Record<string, StoredTaskState>> = this.taskStatesSubject.asObservable();

  private settingsSchemaSubject = new BehaviorSubject<SettingsSchemaBundle>({
    audio: null,
    llm: null
  });
  public settingsSchema$: Observable<SettingsSchemaBundle> = this.settingsSchemaSubject.asObservable();

  constructor(
    private http: HttpClient,
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

  setCharacterList(list: string): void {
    this.patchContentState({ characterList: list });
  }

  getCharacterList(): string {
    return this.characterListSubject.value;
  }

  setSummary(summary: string): void {
    this.patchContentState({ summary });
  }

  getSummary(): string {
    return this.summarySubject.value;
  }

  setSynopsis(synopsis: string): void {
    this.patchContentState({ synopsis });
  }

  getSynopsis(): string {
    return this.synopsisSubject.value;
  }

  setRecap(recap: string): void {
    this.patchContentState({ recap });
  }

  getRecap(): string {
    return this.recapSubject.value;
  }

  setAdditionalInstructions(instructions: string): void {
    this.patchContentState({ additionalInstructions: instructions });
  }

  getAdditionalInstructions(): string {
    return this.additionalInstructionsSubject.value;
  }

  setContextState(context: Partial<AppContentState>): void {
    this.patchContentState(context);
  }

  setActiveSubtitleFile(file: File | null): void {
    this.activeSubtitleFileSubject.next(file);
    this.setSubtitleFileInfo(null);
    this.setSubtitleFileInfoError('');
    this.loadMatchingContextForSubtitle(file);
  }

  getActiveSubtitleFile(): File | null {
    return this.activeSubtitleFileSubject.value;
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

  getState(): Observable<AppContentState> {
    return new Observable(observer => {
      observer.next(this.contentStateSubject.value);
      observer.complete();
    });
  }

  setSettingsSchema(schema: SettingsSchemaBundle): void {
    this.settingsSchemaSubject.next(schema);
  }

  getSettingsSchema(): SettingsSchemaBundle {
    return this.settingsSchemaSubject.value;
  }

  private patchContentState(patch: Partial<AppContentState>): void {
    const next = { ...this.contentStateSubject.value, ...patch };
    this.contentStateSubject.next(next);
    this.characterListSubject.next(next.characterList);
    this.synopsisSubject.next(next.synopsis);
    this.summarySubject.next(next.summary);
    this.recapSubject.next(next.recap);
    this.additionalInstructionsSubject.next(next.additionalInstructions);
  }

  private loadMatchingContextForSubtitle(file: File | null): void {
    if (!file) return;
    const baseName = file.name.replace(/\.(ass|srt)$/i, '');
    const contextFilename = `${baseName}.json`;
    this.http.get<ContextFileData>(
      `${this.baseUrl}/file-management/context-files/${encodeURIComponent(contextFilename)}`
    ).subscribe({
      next: (data) => {
        const patch: Partial<AppContentState> = {};
        if (data.additionalInstructions !== undefined) patch.additionalInstructions = data.additionalInstructions;
        if (data.characterList !== undefined) patch.characterList = data.characterList;
        if (data.synopsis !== undefined) patch.synopsis = data.synopsis;
        if (data.summary !== undefined) patch.summary = data.summary;
        if (data.recap !== undefined) patch.recap = data.recap;
        this.setContextState(patch);
      },
      error: (error) => {
        if (error.status !== 404) {
          console.error('Error loading context file:', error);
          alert('Failed to load context file.');
        }
      }
    });
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
