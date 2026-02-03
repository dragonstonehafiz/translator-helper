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
  @Input() avgSecondsPerLine = 0;
  @Input() etaSeconds = 0;

  get percent(): number {
    if (!this.total) return 0;
    return Math.min(100, Math.max(0, (this.current / this.total) * 100));
  }

  get formattedAvg(): string {
    const value = Number.isFinite(this.avgSecondsPerLine) ? this.avgSecondsPerLine : 0;
    return `${value.toFixed(2)}s/line`;
  }

  get formattedEta(): string {
    const safeValue = Math.max(0, Number.isFinite(this.etaSeconds) ? this.etaSeconds : 0);
    const totalSeconds = Math.round(safeValue);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `Est. Time Left: ${minutes}:${seconds.toString().padStart(2, '0')}`;
  }
}
