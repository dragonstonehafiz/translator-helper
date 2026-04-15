import { CommonModule } from '@angular/common';
import { Component, EventEmitter, HostListener, Input, Output } from '@angular/core';
import { PrimaryButtonComponent } from '../primary-button/primary-button.component';
import { ErrorDialogState } from '../../services/error-dialog.service';

@Component({
  selector: 'app-error-dialog',
  standalone: true,
  imports: [CommonModule, PrimaryButtonComponent],
  templateUrl: './error-dialog.component.html',
  styleUrl: './error-dialog.component.scss'
})
export class ErrorDialogComponent {
  @Input({ required: true }) dialog!: ErrorDialogState;
  @Output() dismissed = new EventEmitter<void>();

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.dismissed.emit();
  }

  onBackdropClick(): void {
    this.dismissed.emit();
  }

  onPanelClick(event: MouseEvent): void {
    event.stopPropagation();
  }
}
