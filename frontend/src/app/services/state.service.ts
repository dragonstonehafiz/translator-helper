import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class StateService {
  private isReadySubject = new BehaviorSubject<boolean>(false);
  public isReady$: Observable<boolean> = this.isReadySubject.asObservable();

  private loadingWhisperSubject = new BehaviorSubject<boolean>(false);
  public loadingWhisper$: Observable<boolean> = this.loadingWhisperSubject.asObservable();

  private loadingGptSubject = new BehaviorSubject<boolean>(false);
  public loadingGpt$: Observable<boolean> = this.loadingGptSubject.asObservable();

  private loadingTavilySubject = new BehaviorSubject<boolean>(false);
  public loadingTavily$: Observable<boolean> = this.loadingTavilySubject.asObservable();

  // Context data
  private webContextSubject = new BehaviorSubject<string>('');
  public webContext$: Observable<string> = this.webContextSubject.asObservable();

  private characterListSubject = new BehaviorSubject<string>('');
  public characterList$: Observable<string> = this.characterListSubject.asObservable();

  private summarySubject = new BehaviorSubject<string>('');
  public summary$: Observable<string> = this.summarySubject.asObservable();

  private runningContextSubject = new BehaviorSubject<boolean>(false);
  public runningContext$: Observable<boolean> = this.runningContextSubject.asObservable();

  constructor() { }

  setReady(ready: boolean): void {
    this.isReadySubject.next(ready);
  }

  getReady(): boolean {
    return this.isReadySubject.value;
  }

  setLoadingWhisper(loading: boolean): void {
    this.loadingWhisperSubject.next(loading);
  }

  setLoadingGpt(loading: boolean): void {
    this.loadingGptSubject.next(loading);
  }

  setLoadingTavily(loading: boolean): void {
    this.loadingTavilySubject.next(loading);
  }

  setWebContext(context: string): void {
    this.webContextSubject.next(context);
  }

  getWebContext(): string {
    return this.webContextSubject.value;
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

  setRunningContext(running: boolean): void {
    this.runningContextSubject.next(running);
  }

  getRunningContext(): boolean {
    return this.runningContextSubject.value;
  }
}
