import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-progress-bar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './progress-bar.component.html',
  styleUrl: './progress-bar.component.scss'
})
export class ProgressBarComponent {
  @Input() current = 0;
  @Input() total = 0;
  @Input() labelColor = '#5568d3';

  get percent(): number {
    if (!this.total) return 0;
    return Math.min(100, Math.max(0, (this.current / this.total) * 100));
  }
}
