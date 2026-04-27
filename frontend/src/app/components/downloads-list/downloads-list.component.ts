import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PrimaryButtonComponent } from '../primary-button/primary-button.component';

@Component({
  selector: 'app-downloads-list',
  standalone: true,
  imports: [CommonModule, FormsModule, PrimaryButtonComponent],
  templateUrl: './downloads-list.component.html',
  styleUrl: './downloads-list.component.scss'
})
export class DownloadsListComponent {
  @Input() title = 'Downloads';
  @Input() files: { name: string; size: number; modified: string }[] = [];
  @Input() isLoading = false;
  @Input() error = '';
  @Input() deletingFilename = '';
  @Input() collapsed = false;
  @Input() pageSize = 7;
  @Output() collapsedChange = new EventEmitter<boolean>();
  @Output() refresh = new EventEmitter<void>();
  @Output() download = new EventEmitter<string>();
  @Output() delete = new EventEmitter<string>();

  search = '';
  sortField: 'modified' | 'name' = 'name';
  sort: 'desc' | 'asc' = 'asc';
  currentPage = 1;

  toggleCollapsed(): void {
    this.collapsed = !this.collapsed;
    this.collapsedChange.emit(this.collapsed);
  }

  setSort(order: 'asc' | 'desc'): void {
    this.sort = order;
    this.currentPage = 1;
  }

  onSearchChange(): void {
    this.currentPage = 1;
  }

  onSortFieldChange(): void {
    this.currentPage = 1;
  }

  goToPage(page: number): void {
    this.currentPage = Math.min(Math.max(page, 1), this.totalPages);
  }

  get normalizedPageSize(): number {
    return Number.isFinite(this.pageSize) && this.pageSize > 0 ? Math.floor(this.pageSize) : 7;
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.filteredFiles.length / this.normalizedPageSize), 1);
  }

  get visiblePage(): number {
    return Math.min(this.currentPage, this.totalPages);
  }

  get pageStartIndex(): number {
    if (this.filteredFiles.length === 0) return 0;
    return (this.visiblePage - 1) * this.normalizedPageSize + 1;
  }

  get pageEndIndex(): number {
    return Math.min(this.visiblePage * this.normalizedPageSize, this.filteredFiles.length);
  }

  get paginatedFiles(): { name: string; size: number; modified: string }[] {
    const start = (this.visiblePage - 1) * this.normalizedPageSize;
    return this.filteredFiles.slice(start, start + this.normalizedPageSize);
  }

  get filteredFiles(): { name: string; size: number; modified: string }[] {
    const search = this.search.trim().toLowerCase();
    let list = this.files;
    if (search) {
      list = list.filter(file => file.name.toLowerCase().includes(search));
    }
    const direction = this.sort === 'asc' ? 1 : -1;
    return [...list].sort((a, b) => {
      if (this.sortField === 'name') {
        return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }) * direction;
      }
      const aTime = Date.parse(a.modified);
      const bTime = Date.parse(b.modified);
      if (!Number.isNaN(aTime) && !Number.isNaN(bTime)) {
        return (aTime - bTime) * direction;
      }
      return a.modified.localeCompare(b.modified) * direction;
    });
  }

  formatBytes(bytes: number): string {
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / Math.pow(1024, index);
    return `${value.toFixed(value < 10 && index > 0 ? 1 : 0)} ${units[index]}`;
  }
}
