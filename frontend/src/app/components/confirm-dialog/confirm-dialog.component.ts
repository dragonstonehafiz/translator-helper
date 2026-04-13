import { CommonModule } from '@angular/common';
import { Component, EventEmitter, HostListener, Input, Output } from '@angular/core';
import { PrimaryButtonComponent } from '../primary-button/primary-button.component';
import { ConfirmationDialogState } from '../../services/confirmation.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, PrimaryButtonComponent],
  templateUrl: './confirm-dialog.component.html',
  styleUrl: './confirm-dialog.component.scss'
})
export class ConfirmDialogComponent {
  @Input({ required: true }) dialog!: ConfirmationDialogState;
  @Output() confirmed = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.cancelled.emit();
  }

  onBackdropClick(): void {
    this.cancelled.emit();
  }

  onPanelClick(event: MouseEvent): void {
    event.stopPropagation();
  }
}
