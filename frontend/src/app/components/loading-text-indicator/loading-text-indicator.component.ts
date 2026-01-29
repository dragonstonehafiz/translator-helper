import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-text-indicator',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './loading-text-indicator.component.html',
  styleUrl: './loading-text-indicator.component.scss'
})
export class LoadingTextIndicatorComponent {
  @Input() text = 'Loading...';
  @Input() color = '#667eea';
  @Input() size = '1.5rem';
  @Input() weight = 700;
}
