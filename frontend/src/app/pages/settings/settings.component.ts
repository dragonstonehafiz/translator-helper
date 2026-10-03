import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable, Subscription, interval } from 'rxjs';
import { ApiResponse, ApiService } from '../../services/api.service';
import {
  SettingsField,
  SettingsSchema,
  SettingsSchemaBundle,
  SettingsValue,
  StateService
} from '../../services/state.service';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { TabsComponent } from '../../components/tabs/tabs.component';
import { TabComponent } from '../../components/tabs/tab.component';
import { ErrorDialogService } from '../../services/error-dialog.service';

type ModelScope = 'llm' | 'audio' | 'search';

const SCOPE_LABELS: Record<ModelScope, string> = {
  llm: 'LLM',
  audio: 'transcription model',
  search: 'web search',
};

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, PrimaryButtonComponent, TooltipIconComponent, TabsComponent, TabComponent],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit, OnDestroy {
  llmReady: boolean | null = null;
  audioReady: boolean | null = null;
  searchReady: boolean | null = null;

  llmLoadingError: string | null = null;
  audioLoadingError: string | null = null;
  searchLoadingError: string | null = null;

  loadingAudio = false;
  loadingLlm = false;
  loadingSearch = false;

  llmDetails: Array<{ label: string; value: string }> = [];
  audioDetails: Array<{ label: string; value: string }> = [];

  audioSchema: SettingsSchema | null = null;
  llmSchema: SettingsSchema | null = null;
  searchSchema: SettingsSchema | null = null;

  settingsValues: Record<ModelScope, Record<string, SettingsValue>> = {
    audio: {},
    llm: {},
    search: {}
  };

  private statusPollSub: Subscription | null = null;
  private lastShownLlmError: string | null = null;
  private lastShownAudioError: string | null = null;
  private lastShownSearchError: string | null = null;

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.loadSettingsSchema();
    this.loadFromState();

    this.stateService.loadingAudio$.subscribe(loading => {
      this.loadingAudio = loading;
    });

    this.stateService.loadingLlm$.subscribe(loading => {
      this.loadingLlm = loading;
    });

    this.startStatusPolling();
    this.loadServerVariables();
  }

  ngOnDestroy(): void {
    if (this.statusPollSub) {
      this.statusPollSub.unsubscribe();
      this.statusPollSub = null;
    }
  }

  private startStatusPolling(): void {
    if (this.statusPollSub) {
      return;
    }

    this.statusPollSub = interval(1000).subscribe(() => {
      this.loadServerVariables();
      this.loadRunningStatus();
    });
  }

  checkStatus(): void {
    this.loadServerVariables();
    this.loadRunningStatus();
  }

  loadSettingsSchema(): void {
    const cachedSchema = this.stateService.getSettingsSchema();
    if (cachedSchema.audio || cachedSchema.llm || cachedSchema.search) {
      this.applySchema(cachedSchema, false);
      return;
    }
    this.fetchSchema(false);
  }

  /** Fetch the schema from the backend; `overwrite` replaces the form values with the saved ones. */
  private fetchSchema(overwrite: boolean): void {
    this.apiService.getSettingsSchema().subscribe({
      next: (schema) => {
        if (!schema.data) return;
        this.stateService.setSettingsSchema(schema.data);
        this.applySchema(schema.data, overwrite);
      },
      error: (error) => {
        console.error('Failed to load settings schema:', error);
        this.errorDialogService.show('Failed to load settings schema');
      }
    });
  }

  loadServerVariables(): void {
    this.apiService.getServerVariables().subscribe({
      next: (response) => {
        if (!response.data) return;
        const audioVars = Array.isArray(response.data.audio) ? response.data.audio : [];
        const llmVars = Array.isArray(response.data.llm) ? response.data.llm : [];

        this.stateService.setLlmReady(response.data.llm_ready);
        this.stateService.setAudioReady(response.data.audio_ready);
        this.stateService.setSearchReady(response.data.search_ready ?? null);
        this.stateService.setReady(response.data.llm_ready && response.data.audio_ready);
        this.llmReady = response.data.llm_ready;
        this.audioReady = response.data.audio_ready;
        this.searchReady = response.data.search_ready ?? null;
        this.llmLoadingError = response.data.llm_loading_error ?? null;
        this.audioLoadingError = response.data.audio_loading_error ?? null;
        this.searchLoadingError = response.data.search_loading_error ?? null;
        this.showLoadErrorIfNeeded('llm', this.llmLoadingError);
        this.showLoadErrorIfNeeded('audio', this.audioLoadingError);
        this.showLoadErrorIfNeeded('search', this.searchLoadingError);

        this.audioDetails = audioVars.map(item => ({
          label: item.label ?? item.key ?? '',
          value: String(item.value)
        }));
        this.llmDetails = llmVars.map(item => ({
          label: item.label ?? item.key ?? '',
          value: String(item.value)
        }));

        this.stateService.setServerVariables({
          audio: audioVars,
          llm: llmVars
        });
      },
      error: (error) => {
        console.error('Failed to load server variables:', error);
        this.llmReady = null;
        this.audioReady = null;
        this.searchReady = null;
        this.stateService.setLlmReady(null);
        this.stateService.setAudioReady(null);
        this.stateService.setSearchReady(null);
      }
    });
  }

  private loadRunningStatus(): void {
    this.apiService.checkRunning().subscribe({
      next: (status) => {
        if (!status.data) return;
        this.stateService.setLoadingLlm(status.data.loading_llm_model);
        this.stateService.setLoadingAudio(status.data.loading_audio_model);
        this.loadingSearch = status.data.loading_search_model;
      },
      error: (error) => {
        console.error('Failed to load running status:', error);
      }
    });
  }

  loadFromState(): void {
    const llmReady = this.stateService.getLlmReady();
    const audioReady = this.stateService.getAudioReady();
    const searchReady = this.stateService.getSearchReady();
    const serverVars = this.stateService.getServerVariables();

    if (llmReady !== null) {
      this.llmReady = llmReady;
    }
    if (audioReady !== null) {
      this.audioReady = audioReady;
    }
    if (searchReady !== null) {
      this.searchReady = searchReady;
    }
    const cachedAudio = Array.isArray(serverVars.audio) ? serverVars.audio : [];
    const cachedLlm = Array.isArray(serverVars.llm) ? serverVars.llm : [];
    this.audioDetails = cachedAudio.map(item => ({
      label: item.label ?? item.key ?? '',
      value: String(item.value)
    }));
    this.llmDetails = cachedLlm.map(item => ({
      label: item.label ?? item.key ?? '',
      value: String(item.value)
    }));

    if (llmReady === null || audioReady === null) {
      this.checkStatus();
    }
  }

  isLoading(scope: ModelScope): boolean {
    return scope === 'llm' ? this.loadingLlm : scope === 'audio' ? this.loadingAudio : this.loadingSearch;
  }

  isFieldDisabled(scope: ModelScope): boolean {
    const ready = scope === 'llm' ? this.llmReady : scope === 'audio' ? this.audioReady : this.searchReady;
    return this.isLoading(scope) || ready === null;
  }

  passwordPlaceholder(field: SettingsField): string {
    return field.is_set ? 'Saved (leave blank to keep)' : (field.placeholder ?? '');
  }

  /** Validate the form against its schema, then save the settings and initialize the model. */
  reloadModel(scope: ModelScope): void {
    if (this.isLoading(scope)) return;
    const schema = this.schemaFor(scope);
    if (!schema) return;

    const missing = schema.fields.find(field => field.required && this.isEmpty(this.settingsValues[scope][field.key]) && !field.is_set);
    if (missing) {
      this.errorDialogService.show(`Please enter ${missing.label}`);
      return;
    }

    const settings: Record<string, SettingsValue> = {};
    for (const field of schema.fields) {
      const value = this.settingsValues[scope][field.key];
      if (value === undefined || (field.type === 'password' && this.isEmpty(value))) continue;
      settings[field.key] = value;
    }

    this.setLoading(scope, true);
    this.loadRequest(scope, settings).subscribe({
      next: (response) => {
        this.setLoading(scope, false);
        if (response.status === 'error') {
          this.errorDialogService.show(response.message || `Failed to load ${SCOPE_LABELS[scope]}`);
        }
        this.clearPasswords(scope);
        this.fetchSchema(true);
        this.loadServerVariables();
      },
      error: (error) => {
        console.error(`Failed to load ${SCOPE_LABELS[scope]}:`, error);
        this.setLoading(scope, false);
        this.errorDialogService.show(`Failed to load ${SCOPE_LABELS[scope]}`);
      }
    });
  }

  private loadRequest(scope: ModelScope, settings: Record<string, SettingsValue>): Observable<ApiResponse<null>> {
    if (scope === 'llm') return this.apiService.loadLlmModel(settings);
    if (scope === 'audio') return this.apiService.loadAudioModel(settings);
    return this.apiService.loadSearchModel(settings);
  }

  private setLoading(scope: ModelScope, loading: boolean): void {
    if (scope === 'llm') this.stateService.setLoadingLlm(loading);
    else if (scope === 'audio') this.stateService.setLoadingAudio(loading);
    else this.loadingSearch = loading;
  }

  private schemaFor(scope: ModelScope): SettingsSchema | null {
    return scope === 'llm' ? this.llmSchema : scope === 'audio' ? this.audioSchema : this.searchSchema;
  }

  private isEmpty(value: SettingsValue | undefined): boolean {
    return value === undefined || value === null || (typeof value === 'string' && !value.trim());
  }

  private clearPasswords(scope: ModelScope): void {
    for (const field of this.schemaFor(scope)?.fields ?? []) {
      if (field.type === 'password') this.settingsValues[scope][field.key] = '';
    }
  }

  private applySchema(schema: SettingsSchemaBundle, overwrite: boolean): void {
    this.audioSchema = schema.audio;
    this.llmSchema = schema.llm;
    this.searchSchema = schema.search ?? null;

    this.initializeSettingsValues('audio', this.audioSchema, overwrite);
    this.initializeSettingsValues('llm', this.llmSchema, overwrite);
    this.initializeSettingsValues('search', this.searchSchema, overwrite);
  }

  /** Fill form values from the schema's current values; existing edits are kept unless `overwrite` is set. */
  private initializeSettingsValues(scope: ModelScope, schema: SettingsSchema | null, overwrite: boolean): void {
    if (!schema) return;

    schema.fields.forEach(field => {
      if (overwrite || this.settingsValues[scope][field.key] === undefined) {
        this.settingsValues[scope][field.key] = field.value ?? field.default;
      }
    });
  }

  private showLoadErrorIfNeeded(scope: ModelScope, message: string | null): void {
    if (!message) {
      if (scope === 'llm') this.lastShownLlmError = null;
      else if (scope === 'audio') this.lastShownAudioError = null;
      else this.lastShownSearchError = null;
      return;
    }

    if (scope === 'llm') {
      if (this.lastShownLlmError === message) return;
      this.lastShownLlmError = message;
    } else if (scope === 'audio') {
      if (this.lastShownAudioError === message) return;
      this.lastShownAudioError = message;
    } else {
      if (this.lastShownSearchError === message) return;
      this.lastShownSearchError = message;
    }

    this.errorDialogService.show(message);
  }
}
