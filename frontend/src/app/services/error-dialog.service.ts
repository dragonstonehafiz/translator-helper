import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface ErrorDialogOptions {
  title?: string;
  message: string;
  acknowledgeLabel?: string;
}

export interface ErrorDialogState {
  title: string;
  message: string;
  acknowledgeLabel: string;
}

@Injectable({
  providedIn: 'root'
})
export class ErrorDialogService {
  private readonly dialogSubject = new BehaviorSubject<ErrorDialogState | null>(null);

  readonly dialog$ = this.dialogSubject.asObservable();

  show(options: ErrorDialogOptions | string): void {
    const normalized = typeof options === 'string'
      ? { message: options }
      : options;

    this.dialogSubject.next({
      title: normalized.title ?? 'Error',
      message: normalized.message,
      acknowledgeLabel: normalized.acknowledgeLabel ?? 'OK',
    });
  }

  dismiss(): void {
    this.dialogSubject.next(null);
  }
}
