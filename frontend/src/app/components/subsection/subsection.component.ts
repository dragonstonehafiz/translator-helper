import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-subsection',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './subsection.component.html',
  styleUrl: './subsection.component.scss'
})
export class SubsectionComponent {
  @Input() title: string = '';
  @Input() collapsed: boolean = false;
  @Input() tooltip: string = '';

  toggleCollapse(): void {
    this.collapsed = !this.collapsed;
  }
}
