import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-tab',
  standalone: true,
  imports: [CommonModule],
  template: `<ng-content></ng-content>`,
  host: { '[hidden]': '!active' }
})
export class TabComponent {
  @Input() label: string = '';
  active: boolean = false;
}
