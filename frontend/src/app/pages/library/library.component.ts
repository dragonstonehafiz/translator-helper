import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, SeriesSummary } from '../../services/api.service';
import { ConfirmationService } from '../../services/confirmation.service';
import { ErrorDialogService } from '../../services/error-dialog.service';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { SecondaryButtonComponent } from '../../components/secondary-button/secondary-button.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { LANGUAGE_OPTIONS } from '../../shared/language-options';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, PrimaryButtonComponent, SecondaryButtonComponent, LoadingTextIndicatorComponent],
  templateUrl: './library.component.html',
  styleUrl: './library.component.scss'
})
export class LibraryComponent implements OnInit {
  languageOptions = LANGUAGE_OPTIONS;

  seriesList: SeriesSummary[] = [];
  isLoadingSeries = false;

  showCreateForm = false;
  newSeriesName = 'Gakuen Idolmaster';
  newSeriesInputLang = 'ja';
  newSeriesOutputLang = 'en';
  newSeriesNotes = '';
  isCreatingSeries = false;

  constructor(
    private router: Router,
    private apiService: ApiService,
    private confirmationService: ConfirmationService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.loadSeriesList();
  }

  loadSeriesList(): void {
    this.isLoadingSeries = true;
    this.apiService.listSeries().subscribe({
      next: (response) => {
        this.seriesList = response.data?.series ?? [];
        this.isLoadingSeries = false;
      },
      error: () => {
        this.isLoadingSeries = false;
        this.errorDialogService.show('Failed to load series list.');
      }
    });
  }

  openSeries(seriesId: string): void {
    this.router.navigate(['/library', seriesId]);
  }

  openCreateForm(): void {
    this.showCreateForm = true;
    this.newSeriesName = 'Gakuen Idolmaster';
    this.newSeriesInputLang = 'ja';
    this.newSeriesOutputLang = 'en';
    this.newSeriesNotes = '';
  }

  cancelCreateForm(): void {
    this.showCreateForm = false;
  }

  createSeries(): void {
    if (!this.newSeriesName.trim() || this.isCreatingSeries) return;
    this.isCreatingSeries = true;
    this.apiService.createSeries({
      name: this.newSeriesName.trim(),
      input_lang: this.newSeriesInputLang,
      output_lang: this.newSeriesOutputLang,
      notes: this.newSeriesNotes.trim(),
    }).subscribe({
      next: (response) => {
        this.isCreatingSeries = false;
        this.showCreateForm = false;
        const newId = response.data?.id;
        if (newId) {
          this.router.navigate(['/library', newId]);
        } else {
          this.loadSeriesList();
        }
      },
      error: () => {
        this.isCreatingSeries = false;
        this.errorDialogService.show('Failed to create series.');
      }
    });
  }

  async deleteSeries(seriesId: string, seriesName: string): Promise<void> {
    const confirmed = await this.confirmationService.confirm({
      title: 'Delete Series',
      message: `Delete "${seriesName}" and all its characters and glossary terms? This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.apiService.deleteSeries(seriesId).subscribe({
      next: () => this.loadSeriesList(),
      error: () => this.errorDialogService.show('Failed to delete series.')
    });
  }
}
