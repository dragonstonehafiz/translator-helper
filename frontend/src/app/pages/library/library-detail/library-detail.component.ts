import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule, KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { ApiService, SeriesData, LibraryProposals, SeriesCharacter, SeriesGlossaryTerm } from '../../../services/api.service';
import { StateService, TASK_TYPES } from '../../../services/state.service';
import { ConfirmationService } from '../../../services/confirmation.service';
import { ErrorDialogService } from '../../../services/error-dialog.service';
import { SubsectionComponent } from '../../../components/subsection/subsection.component';
import { PrimaryButtonComponent } from '../../../components/primary-button/primary-button.component';
import { FileUploadComponent } from '../../../components/file-upload/file-upload.component';
import { LoadingTextIndicatorComponent } from '../../../components/loading-text-indicator/loading-text-indicator.component';
import { TabsComponent } from '../../../components/tabs/tabs.component';
import { TabComponent } from '../../../components/tabs/tab.component';
import { LANGUAGE_OPTIONS } from '../../../shared/language-options';

@Component({
  selector: 'app-library-detail',
  standalone: true,
  imports: [CommonModule, KeyValuePipe, FormsModule, SubsectionComponent, PrimaryButtonComponent, FileUploadComponent, LoadingTextIndicatorComponent, TabsComponent, TabComponent],
  templateUrl: './library-detail.component.html',
  styleUrl: './library-detail.component.scss'
})
export class LibraryDetailComponent implements OnInit, OnDestroy {
  languageOptions = LANGUAGE_OPTIONS;

  series: SeriesData | null = null;
  isLoading = false;

  // Edit series
  editSeriesName = '';
  editSeriesInputLang = 'ja';
  editSeriesOutputLang = 'en';
  editSeriesNotes = '';
  isSavingSeriesEdit = false;

  // Character form
  showAddCharacterForm = false;
  editingCharacterId: string | null = null;
  charName = '';
  charAliases = '';
  charPersonality: string[] = [];
  charRelationships: { character: string; facts: string[] }[] = [];
  charHistory: string[] = [];
  newPersonality = '';
  newRelationshipCharacter = '';
  newRelationshipDetail = '';
  newHistory = '';
  isSavingCharacter = false;

  // Glossary form
  showAddGlossaryForm = false;
  editingTermId: string | null = null;
  termTerm = '';
  termTranslation = '';
  termNotes = '';
  isSavingTerm = false;

  // Library update
  updateSubtitleFile: File | null = null;  // mirrors shared activeSubtitleFile$
  isUpdatingLibrary = false;
  proposals: LibraryProposals | null = null;
  searchReady: boolean | null = null;
  private pollingSubscription?: Subscription;

  // Expanded character cards
  expandedCharacterIds = new Set<string>();

  private seriesId = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
    private stateService: StateService,
    private confirmationService: ConfirmationService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.seriesId = this.route.snapshot.paramMap.get('seriesId') ?? '';
    this.searchReady = this.stateService.getSearchReady();
    this.stateService.searchReady$.subscribe(r => this.searchReady = r);
    this.updateSubtitleFile = this.stateService.getActiveSubtitleFile();
    this.stateService.activeSubtitleFile$.subscribe(f => this.updateSubtitleFile = f);
    this.loadSeries();
    this.resumePollingIfNeeded();
  }

  ngOnDestroy(): void {
    this.pollingSubscription?.unsubscribe();
  }

  // ── Series ───────────────────────────────────────────────────────────────────

  loadSeries(): void {
    this.isLoading = true;
    this.apiService.getSeries(this.seriesId).subscribe({
      next: (response) => {
        this.series = response.data ?? null;
        this.isLoading = false;
        if (this.series) {
          this.editSeriesName = this.series.name;
          this.editSeriesInputLang = this.series.input_lang;
          this.editSeriesOutputLang = this.series.output_lang;
          this.editSeriesNotes = this.series.notes;
        }
      },
      error: () => {
        this.isLoading = false;
        this.errorDialogService.show('Failed to load series.');
        this.router.navigate(['/library']);
      }
    });
  }

  saveSeriesEdit(): void {
    if (!this.series || !this.editSeriesName.trim() || this.isSavingSeriesEdit) return;
    this.isSavingSeriesEdit = true;
    this.apiService.updateSeries(this.series.id, {
      name: this.editSeriesName.trim(),
      input_lang: this.editSeriesInputLang,
      output_lang: this.editSeriesOutputLang,
      notes: this.editSeriesNotes.trim(),
    }).subscribe({
      next: (response) => {
        this.series = response.data ?? this.series;
        this.isSavingSeriesEdit = false;
      },
      error: () => {
        this.isSavingSeriesEdit = false;
        this.errorDialogService.show('Failed to save series changes.');
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/library']);
  }

  // ── Characters ───────────────────────────────────────────────────────────────

  toggleCharacter(characterId: string): void {
    if (this.expandedCharacterIds.has(characterId)) {
      this.expandedCharacterIds.delete(characterId);
    } else {
      this.expandedCharacterIds.add(characterId);
    }
  }

  openAddCharacterForm(): void {
    this.editingCharacterId = null;
    this.charName = '';
    this.charAliases = '';
    this.charPersonality = [];
    this.charRelationships = [] as { character: string; facts: string[] }[];
    this.charHistory = [];
    this.newPersonality = '';
    this.newRelationshipCharacter = '';
    this.newRelationshipDetail = '';
    this.newHistory = '';
    this.showAddCharacterForm = true;
  }

  openEditCharacterForm(char: SeriesCharacter): void {
    this.showAddCharacterForm = false;
    this.editingCharacterId = char.id;
    this.charName = char.name;
    this.charAliases = char.aliases.join(', ');
    this.charPersonality = [...char.personality];
    this.charRelationships = Object.entries(char.relationships ?? {}).map(([k, facts]) => ({ character: k, facts: [...(facts ?? [])] }));
    this.charHistory = [...char.history];
    this.newPersonality = '';
    this.newRelationshipCharacter = '';
    this.newRelationshipDetail = '';
    this.newHistory = '';
    this.expandedCharacterIds.add(char.id);
  }

  cancelCharacterForm(): void {
    this.showAddCharacterForm = false;
    this.editingCharacterId = null;
  }

  addPersonalityEntry(): void {
    if (this.newPersonality.trim()) {
      this.charPersonality.push(this.newPersonality.trim());
      this.newPersonality = '';
    }
  }

  removePersonalityEntry(i: number): void {
    this.charPersonality.splice(i, 1);
  }

  addRelationshipEntry(): void {
    const character = this.newRelationshipCharacter.trim();
    const fact = this.newRelationshipDetail.trim();
    if (character && fact) {
      const group = this.charRelationships.find(g => g.character === character);
      if (group) group.facts.push(fact);
      else this.charRelationships.push({ character, facts: [fact] });
      this.newRelationshipCharacter = '';
      this.newRelationshipDetail = '';
    }
  }

  removeRelationshipFact(gi: number, fi: number): void {
    this.charRelationships[gi].facts.splice(fi, 1);
    if (this.charRelationships[gi].facts.length === 0) this.charRelationships.splice(gi, 1);
  }

  getRelationshipEntries(relationships: { [character: string]: string[] } | any): [string, string[]][] {
    if (!relationships || typeof relationships !== 'object' || Array.isArray(relationships)) return [];
    return Object.entries(relationships) as [string, string[]][];
  }

  private relationshipsToDict(): { [character: string]: string[] } {
    const dict: { [character: string]: string[] } = {};
    for (const { character, facts } of this.charRelationships) {
      if (!character.trim()) continue;
      dict[character.trim()] = facts.filter(f => f.trim());
    }
    return dict;
  }

  addHistoryEntry(): void {
    if (this.newHistory.trim()) {
      this.charHistory.push(this.newHistory.trim());
      this.newHistory = '';
    }
  }

  removeHistoryEntry(i: number): void {
    this.charHistory.splice(i, 1);
  }

  saveCharacter(): void {
    if (!this.series || !this.charName.trim() || this.isSavingCharacter) return;
    this.isSavingCharacter = true;
    const payload = {
      name: this.charName.trim(),
      aliases: this.charAliases.split(',').map(a => a.trim()).filter(Boolean),
      personality: this.charPersonality,

      relationships: this.relationshipsToDict(),
      history: this.charHistory,
    };
    const request$ = this.editingCharacterId
      ? this.apiService.updateCharacter(this.series.id, this.editingCharacterId, payload)
      : this.apiService.addCharacter(this.series.id, payload);

    request$.subscribe({
      next: (response) => {
        this.series = response.data ?? this.series;
        this.isSavingCharacter = false;
        this.showAddCharacterForm = false;
        this.editingCharacterId = null;
      },
      error: () => {
        this.isSavingCharacter = false;
        this.errorDialogService.show('Failed to save character.');
      }
    });
  }

  async deleteCharacter(characterId: string, characterName: string): Promise<void> {
    if (!this.series) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Delete Character',
      message: `Delete "${characterName}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.apiService.deleteCharacter(this.series.id, characterId).subscribe({
      next: () => {
        if (this.series) {
          this.series = { ...this.series, characters: this.series.characters.filter(c => c.id !== characterId) };
        }
      },
      error: () => this.errorDialogService.show('Failed to delete character.')
    });
  }

  // ── Glossary ─────────────────────────────────────────────────────────────────

  openAddGlossaryForm(): void {
    this.editingTermId = null;
    this.termTerm = '';
    this.termTranslation = '';
    this.termNotes = '';
    this.showAddGlossaryForm = true;
  }

  openEditGlossaryForm(term: SeriesGlossaryTerm): void {
    this.showAddGlossaryForm = false;
    this.editingTermId = term.id;
    this.termTerm = term.term;
    this.termTranslation = term.translation;
    this.termNotes = term.notes;
  }

  cancelGlossaryForm(): void {
    this.showAddGlossaryForm = false;
    this.editingTermId = null;
  }

  saveTerm(): void {
    if (!this.series || !this.termTerm.trim() || !this.termTranslation.trim() || this.isSavingTerm) return;
    this.isSavingTerm = true;
    const payload = { term: this.termTerm.trim(), translation: this.termTranslation.trim(), notes: this.termNotes.trim() };
    const request$ = this.editingTermId
      ? this.apiService.updateGlossaryTerm(this.series.id, this.editingTermId, payload)
      : this.apiService.addGlossaryTerm(this.series.id, payload);

    request$.subscribe({
      next: (response) => {
        this.series = response.data ?? this.series;
        this.isSavingTerm = false;
        this.showAddGlossaryForm = false;
        this.editingTermId = null;
      },
      error: () => {
        this.isSavingTerm = false;
        this.errorDialogService.show('Failed to save glossary term.');
      }
    });
  }

  async deleteTerm(termId: string, term: string): Promise<void> {
    if (!this.series) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Delete Term',
      message: `Delete "${term}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.apiService.deleteGlossaryTerm(this.series.id, termId).subscribe({
      next: () => {
        if (this.series) {
          this.series = { ...this.series, glossary: this.series.glossary.filter(t => t.id !== termId) };
        }
      },
      error: () => this.errorDialogService.show('Failed to delete glossary term.')
    });
  }

  // ── Library Update ───────────────────────────────────────────────────────────

  onUpdateFileSelected(files: File[]): void {
    this.stateService.setActiveSubtitleFile(files[0] ?? null);
  }

  startLibraryUpdate(): void {
    if (!this.series || !this.updateSubtitleFile || this.isUpdatingLibrary) return;
    if (this.stateService.hasActiveTask()) {
      this.errorDialogService.show('Another task is already running.');
      return;
    }
    this.isUpdatingLibrary = true;
    this.proposals = null;

    this.stateService.setTaskState(TASK_TYPES.updateLibrary, {
      status: 'processing',
      result: null,
      message: null,
      progress: { task_type: TASK_TYPES.updateLibrary, current: 0, total: 1, status: 'Starting library update', eta_seconds: 0 },
      isPolling: true,
    });

    this.apiService.startLibraryUpdate(this.series.id, this.updateSubtitleFile).subscribe({
      next: (response) => {
        if (response.status === 'processing') {
          this.startPolling();
        } else {
          this.isUpdatingLibrary = false;
          this.stateService.setTaskState(TASK_TYPES.updateLibrary, { status: 'error', isPolling: false });
          this.errorDialogService.show(response.message || 'Failed to start library update.');
        }
      },
      error: () => {
        this.isUpdatingLibrary = false;
        this.stateService.setTaskState(TASK_TYPES.updateLibrary, { status: 'error', isPolling: false });
        this.errorDialogService.show('Failed to start library update.');
      }
    });
  }

  private startPolling(): void {
    this.pollingSubscription?.unsubscribe();
    this.pollingSubscription = interval(1500).subscribe(() => {
      this.apiService.getTaskResult(TASK_TYPES.updateLibrary).subscribe({
        next: (response) => {
          const taskData = response.data;
          this.stateService.setTaskState(TASK_TYPES.updateLibrary, {
            status: response.status as any,
            result: taskData?.result ?? null,
            progress: taskData?.progress ?? null,
            isPolling: response.status === 'processing',
          });
          if (response.status === 'complete') {
            this.isUpdatingLibrary = false;
            this.proposals = (taskData?.result as any)?.proposals ?? null;
            this.pollingSubscription?.unsubscribe();
          } else if (response.status === 'error') {
            this.isUpdatingLibrary = false;
            this.errorDialogService.show(response.message || 'Library update failed.');
            this.pollingSubscription?.unsubscribe();
          }
        },
        error: (err) => {
          this.isUpdatingLibrary = false;
          this.stateService.setTaskState(TASK_TYPES.updateLibrary, { status: 'error', isPolling: false });
          this.errorDialogService.show(err?.error?.message || 'Failed to poll library update status.');
          this.pollingSubscription?.unsubscribe();
        }
      });
    });
  }

  private resumePollingIfNeeded(): void {
    const taskState = this.stateService.getTaskState(TASK_TYPES.updateLibrary);
    if (taskState.status === 'processing' || taskState.isPolling) {
      this.isUpdatingLibrary = true;
      this.startPolling();
    }
  }

  formatRelationships(relationships: any): string {
    if (Array.isArray(relationships)) {
      return relationships.map((r: any) => typeof r === 'string' ? r : `${r.character} — ${r.detail}`).join(' · ');
    }
    return Object.entries(relationships as { [k: string]: string[] })
      .map(([char, facts]) => `${char}: ${(facts as string[]).join('; ')}`)
      .join(' · ');
  }

  getCharacterName(id: string): string {
    return this.series?.characters.find(c => c.id === id)?.name ?? id;
  }

  getGlossaryTerm(id: string): string {
    return this.series?.glossary.find(t => t.id === id)?.term ?? id;
  }

  acceptNewCharacter(char: any): void {
    if (!this.series) return;
    this.apiService.addCharacter(this.series.id, char).subscribe({
      next: (response) => {
        this.series = response.data ?? this.series;
        if (this.proposals) this.proposals.new_characters = this.proposals.new_characters.filter(c => c !== char);
      },
      error: () => this.errorDialogService.show('Failed to add character.')
    });
  }

  acceptNewGlossaryTerm(term: any): void {
    if (!this.series) return;
    this.apiService.addGlossaryTerm(this.series.id, term).subscribe({
      next: (response) => {
        this.series = response.data ?? this.series;
        if (this.proposals) this.proposals.new_glossary = this.proposals.new_glossary.filter(t => t !== term);
      },
      error: () => this.errorDialogService.show('Failed to add glossary term.')
    });
  }

  acceptCharacterUpdate(update: any): void {
    if (!this.series) return;
    const char = this.series.characters.find(c => c.id === update.id);
    if (!char) {
      this.errorDialogService.show(`Character "${update.id}" not found in library. It may have been deleted.`);
      return;
    }
    let updated: Partial<SeriesCharacter>;
    if (update.field === 'relationships') {
      const existing = { ...char.relationships };
      const charKey = update.character as string;
      existing[charKey] = [...(existing[charKey] || []), update.append];
      updated = { relationships: existing };
    } else {
      const field = update.field as keyof SeriesCharacter;
      updated = { [field]: [...((char[field] as string[]) || []), update.append] };
    }
    this.apiService.updateCharacter(this.series.id, update.id, updated).subscribe({
      next: (response) => {
        this.series = response.data ?? this.series;
        if (this.proposals) this.proposals.updated_characters = this.proposals.updated_characters.filter(u => u !== update);
      },
      error: () => this.errorDialogService.show('Failed to update character.')
    });
  }

  acceptGlossaryUpdate(update: any): void {
    if (!this.series) return;
    const term = this.series.glossary.find(t => t.id === update.id);
    if (!term) {
      this.errorDialogService.show(`Glossary term "${update.id}" not found in library. It may have been deleted.`);
      return;
    }
    const updated = { ...term, [update.field]: update.value };
    this.apiService.updateGlossaryTerm(this.series.id, update.id, updated).subscribe({
      next: (response) => {
        this.series = response.data ?? this.series;
        if (this.proposals) this.proposals.updated_glossary = this.proposals.updated_glossary.filter(u => u !== update);
      },
      error: () => this.errorDialogService.show('Failed to update glossary term.')
    });
  }

  async rejectProposal(list: any[], item: any): Promise<void> {
    const confirmed = await this.confirmationService.confirm({
      title: 'Reject Proposal',
      message: 'Rejecting this proposal will remove it from the list. This cannot be undone.',
      confirmLabel: 'Reject',
      cancelLabel: 'Keep',
    });
    if (!confirmed) return;
    const idx = list.indexOf(item);
    if (idx !== -1) list.splice(idx, 1);
  }
}
