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
}
