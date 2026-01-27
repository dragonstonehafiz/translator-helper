import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TooltipIconComponent } from '../tooltip-icon/tooltip-icon.component';

@Component({
  selector: 'app-subsection',
  standalone: true,
  imports: [CommonModule, TooltipIconComponent],
  templateUrl: './subsection.component.html',
  styleUrl: './subsection.component.scss'
})
export class SubsectionComponent {
  @Input() title: string = '';
  @Input() collapsed: boolean = false;
  @Input() tooltip: string = '';
}
