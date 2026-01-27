import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-context-status',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './context-status.component.html',
  styleUrl: './context-status.component.scss'
})
export class ContextStatusComponent {
  @Input() characterList = '';
  @Input() synopsis = '';
  @Input() summary = '';
  @Input() recap = '';

  hasContent(value: string): boolean {
    return !!value && value.trim().length > 0;
  }
}
