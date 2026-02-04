import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export type SettingsFieldType = 'select' | 'text' | 'password' | 'number' | 'boolean';

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

  private serverAudioVarsSubject = new BehaviorSubject<Array<{ key?: string; label?: string; value?: unknown }> | null>(null);
  public serverAudioVars$: Observable<Array<{ key?: string; label?: string; value?: unknown }> | null> = this.serverAudioVarsSubject.asObservable();
  private serverLlmVarsSubject = new BehaviorSubject<Array<{ key?: string; label?: string; value?: unknown }> | null>(null);
  public serverLlmVars$: Observable<Array<{ key?: string; label?: string; value?: unknown }> | null> = this.serverLlmVarsSubject.asObservable();

  private loadingWhisperSubject = new BehaviorSubject<boolean>(false);
  public loadingWhisper$: Observable<boolean> = this.loadingWhisperSubject.asObservable();

  private loadingGptSubject = new BehaviorSubject<boolean>(false);
  public loadingGpt$: Observable<boolean> = this.loadingGptSubject.asObservable();


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

  private runningLlmSubject = new BehaviorSubject<boolean>(false);
  public runningLlm$: Observable<boolean> = this.runningLlmSubject.asObservable();

  private settingsSchemaSubject = new BehaviorSubject<SettingsSchemaBundle>({
    audio: null,
    llm: null
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

  setLoadingWhisper(loading: boolean): void {
    this.loadingWhisperSubject.next(loading);
  }

  setLoadingGpt(loading: boolean): void {
    this.loadingGptSubject.next(loading);
  }


  setCharacterList(list: string): void {
    this.characterListSubject.next(list);
  }

  getCharacterList(): string {
    return this.characterListSubject.value;
  }

  setSummary(summary: string): void {
    this.summarySubject.next(summary);
  }

  getSummary(): string {
    return this.summarySubject.value;
  }

  setSynopsis(synopsis: string): void {
    this.synopsisSubject.next(synopsis);
  }

  getSynopsis(): string {
    return this.synopsisSubject.value;
  }

  setRecap(recap: string): void {
    this.recapSubject.next(recap);
  }

  getRecap(): string {
    return this.recapSubject.value;
  }

  setAdditionalInstructions(instructions: string): void {
    this.additionalInstructionsSubject.next(instructions);
  }

  getAdditionalInstructions(): string {
    return this.additionalInstructionsSubject.value;
  }

  setRunningLlm(running: boolean): void {
    this.runningLlmSubject.next(running);
  }

  getRunningLlm(): boolean {
    return this.runningLlmSubject.value;
  }

  setSettingsSchema(schema: SettingsSchemaBundle): void {
    this.settingsSchemaSubject.next(schema);
  }

  getSettingsSchema(): SettingsSchemaBundle {
    return this.settingsSchemaSubject.value;
  }

  getState(): Observable<{
    characterList: string;
    synopsis: string;
    summary: string;
    recap: string;
    additionalInstructions: string;
  }> {
    return new Observable(observer => {
      observer.next({
        characterList: this.getCharacterList(),
        synopsis: this.getSynopsis(),
        summary: this.getSummary(),
        recap: this.getRecap(),
        additionalInstructions: this.getAdditionalInstructions()
      });
      observer.complete();
    });
  }
}
