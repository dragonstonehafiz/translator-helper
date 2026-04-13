import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface ConfirmationOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
}

export interface ConfirmationDialogState {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
}

@Injectable({
  providedIn: 'root'
})
export class ConfirmationService {
  private readonly dialogSubject = new BehaviorSubject<ConfirmationDialogState | null>(null);
  private resolver?: (value: boolean) => void;

  readonly dialog$ = this.dialogSubject.asObservable();

  confirm(options: ConfirmationOptions): Promise<boolean> {
    this.resolve(false);

    const dialog: ConfirmationDialogState = {
      title: options.title ?? 'Confirm Action',
      message: options.message,
      confirmLabel: options.confirmLabel ?? 'Confirm',
      cancelLabel: options.cancelLabel ?? 'Cancel',
    };

    this.dialogSubject.next(dialog);

    return new Promise<boolean>((resolve) => {
      this.resolver = resolve;
    });
  }

  resolve(value: boolean): void {
    const resolver = this.resolver;
    this.resolver = undefined;
    this.dialogSubject.next(null);
    resolver?.(value);
  }
}
