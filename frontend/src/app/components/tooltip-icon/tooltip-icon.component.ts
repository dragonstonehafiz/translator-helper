import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-tooltip-icon',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tooltip-icon.component.html',
  styleUrl: './tooltip-icon.component.scss'
})
export class TooltipIconComponent {
  @Input() tooltip = '';
}
