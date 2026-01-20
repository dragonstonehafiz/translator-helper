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
  private openaiReadySubject = new BehaviorSubject<boolean | null>(null);
  public openaiReady$: Observable<boolean | null> = this.openaiReadySubject.asObservable();
  private whisperReadySubject = new BehaviorSubject<boolean | null>(null);
  public whisperReady$: Observable<boolean | null> = this.whisperReadySubject.asObservable();

  private serverWhisperModelSubject = new BehaviorSubject<string | null>(null);
  public serverWhisperModel$: Observable<string | null> = this.serverWhisperModelSubject.asObservable();
  private serverDeviceSubject = new BehaviorSubject<string | null>(null);
  public serverDevice$: Observable<string | null> = this.serverDeviceSubject.asObservable();
  private serverOpenaiModelSubject = new BehaviorSubject<string | null>(null);
  public serverOpenaiModel$: Observable<string | null> = this.serverOpenaiModelSubject.asObservable();
  private serverTemperatureSubject = new BehaviorSubject<number | null>(null);
  public serverTemperature$: Observable<number | null> = this.serverTemperatureSubject.asObservable();

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

  setOpenaiReady(ready: boolean | null): void {
    this.openaiReadySubject.next(ready);
  }

  getOpenaiReady(): boolean | null {
    return this.openaiReadySubject.value;
  }

  setWhisperReady(ready: boolean | null): void {
    this.whisperReadySubject.next(ready);
  }

  getWhisperReady(): boolean | null {
    return this.whisperReadySubject.value;
  }

  setServerVariables(variables: {
    whisperModel: string;
    device: string;
    openaiModel: string;
    temperature: number;
  }): void {
    this.serverWhisperModelSubject.next(variables.whisperModel);
    this.serverDeviceSubject.next(variables.device);
    this.serverOpenaiModelSubject.next(variables.openaiModel);
    this.serverTemperatureSubject.next(variables.temperature);
  }

  getServerVariables(): {
    whisperModel: string | null;
    device: string | null;
    openaiModel: string | null;
    temperature: number | null;
  } {
    return {
      whisperModel: this.serverWhisperModelSubject.value,
      device: this.serverDeviceSubject.value,
      openaiModel: this.serverOpenaiModelSubject.value,
      temperature: this.serverTemperatureSubject.value
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
  }> {
    return new Observable(observer => {
      observer.next({
        characterList: this.getCharacterList(),
        synopsis: this.getSynopsis(),
        summary: this.getSummary(),
        recap: this.getRecap()
      });
      observer.complete();
    });
  }
}
