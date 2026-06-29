import { Component, ContentChildren, QueryList, AfterContentInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TabComponent } from './tab.component';

@Component({
  selector: 'app-tabs',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tabs.component.html',
  styleUrl: './tabs.component.scss'
})
export class TabsComponent implements AfterContentInit {
  @ContentChildren(TabComponent) tabs!: QueryList<TabComponent>;

  activeIndex = 0;

  ngAfterContentInit(): void {
    this.activateTab(this.activeIndex);
  }

  selectTab(index: number): void {
    this.activeIndex = index;
    this.activateTab(index);
  }

  getTabList(): TabComponent[] {
    return this.tabs ? this.tabs.toArray() : [];
  }

  private activateTab(index: number): void {
    this.tabs.toArray().forEach((tab, i) => {
      tab.active = i === index;
    });
  }
}
