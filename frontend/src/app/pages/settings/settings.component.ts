import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription, interval } from 'rxjs';
import { ApiService } from '../../services/api.service';
import {
  SettingsSchema,
  SettingsSchemaBundle,
  StateService
} from '../../services/state.service';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { ErrorDialogService } from '../../services/error-dialog.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, PrimaryButtonComponent, TooltipIconComponent],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit, OnDestroy {
  llmReady: boolean | null = null;
  audioReady: boolean | null = null;

  llmLoadingError: string | null = null;
  audioLoadingError: string | null = null;

  loadingAudio = false;
  loadingLlm = false;

  llmDetails: Array<{ label: string; value: string }> = [];
  audioDetails: Array<{ label: string; value: string }> = [];

  audioSchema: SettingsSchema | null = null;
  llmSchema: SettingsSchema | null = null;
  llmApiKeyRequired = false;

  settingsValues: {
    audio: Record<string, string | number | boolean>;
    llm: Record<string, string | number | boolean>;
  } = {
    audio: {},
    llm: {}
  };

  private statusPollSub: Subscription | null = null;
  private lastShownLlmError: string | null = null;
  private lastShownAudioError: string | null = null;

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.loadSettingsSchema();
    this.loadFromState();

    // Subscribe to loading states
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
    if (cachedSchema.audio || cachedSchema.llm) {
      this.applySchema(cachedSchema);
      return;
    }

    this.apiService.getSettingsSchema().subscribe({
      next: (schema) => {
        if (!schema.data) return;
        this.stateService.setSettingsSchema(schema.data);
        this.applySchema(schema.data);
      },
      error: (error) => {
        console.error('Failed to load settings schema:', error);
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
        this.stateService.setReady(response.data.llm_ready && response.data.audio_ready);
        this.llmReady = response.data.llm_ready;
        this.audioReady = response.data.audio_ready;
        this.llmLoadingError = response.data.llm_loading_error ?? null;
        this.audioLoadingError = response.data.audio_loading_error ?? null;
        this.showLoadErrorIfNeeded('llm', this.llmLoadingError);
        this.showLoadErrorIfNeeded('audio', this.audioLoadingError);
        if (response.data.llm_ready) {
          this.stateService.setLoadingLlm(false);
        }
        if (response.data.audio_ready) {
          this.stateService.setLoadingAudio(false);
        }

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
        this.stateService.setLlmReady(null);
        this.stateService.setAudioReady(null);
      }
    });
  }

  private loadRunningStatus(): void {
    this.apiService.checkRunning().subscribe({
      next: (status) => {
        if (!status.data) return;
        this.stateService.setLoadingLlm(status.data.loading_llm_model);
        this.stateService.setLoadingAudio(status.data.loading_audio_model);
      },
      error: (error) => {
        console.error('Failed to load running status:', error);
      }
    });
  }

  loadFromState(): void {
    const llmReady = this.stateService.getLlmReady();
    const audioReady = this.stateService.getAudioReady();
    const serverVars = this.stateService.getServerVariables();

    if (llmReady !== null) {
      this.llmReady = llmReady;
    }
    if (audioReady !== null) {
      this.audioReady = audioReady;
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

  private applySchema(schema: SettingsSchemaBundle): void {
    this.audioSchema = schema.audio;
    this.llmSchema = schema.llm;
    this.llmApiKeyRequired = Boolean(
      this.llmSchema?.fields.find(field => field.key === 'api_key')?.required
    );

    this.initializeSettingsValues('audio', this.audioSchema);
    this.initializeSettingsValues('llm', this.llmSchema);
  }


  private initializeSettingsValues(scope: 'audio' | 'llm', schema: SettingsSchema | null): void {
    if (!schema) return;

    schema.fields.forEach(field => {
      if (this.settingsValues[scope][field.key] === undefined) {
        if (field.default !== undefined) {
          this.settingsValues[scope][field.key] = field.default;
        }
      }
    });
  }

  loadAudioModel(): void {
    if (this.loadingAudio) return;

    const modelName = this.settingsValues.audio['model_name'] as string | undefined;
    const device = this.settingsValues.audio['device'] as string | undefined;

    if (!modelName || !device) {
      this.errorDialogService.show('Please select a model and device');
      return;
    }

    const settings = { ...this.settingsValues.audio };
    this.stateService.setLoadingAudio(true);

    this.apiService.loadAudioModel(settings).subscribe({
      next: (response) => {
        this.stateService.setLoadingAudio(false);
        if (response.status === 'error') {
          this.errorDialogService.show(response.message || 'Failed to load audio model');
          return;
        }
        this.loadServerVariables();
      },
      error: (error) => {
        console.error('Failed to load audio model:', error);
        this.stateService.setLoadingAudio(false);
        this.errorDialogService.show('Failed to load audio model');
      }
    });
  }

  loadLlmModel(): void {
    if (this.loadingLlm) {
      return;
    }

    const apiKey = this.settingsValues.llm['api_key'] as string | undefined;
    const requiredFields = (this.llmSchema?.fields || []).filter(field => field.required && field.key !== 'api_key');
    for (const field of requiredFields) {
      const value = this.settingsValues.llm[field.key];
      if (value === undefined || value === null || (typeof value === 'string' && !value.trim())) {
        this.errorDialogService.show(`Please enter ${field.label}`);
        return;
      }
    }

    if (this.llmApiKeyRequired && !apiKey && this.llmReady === false) {
      this.errorDialogService.show('Please enter OpenAI API key');
      return;
    }

    const settings = { ...this.settingsValues.llm };
    if (typeof settings['api_key'] === 'string' && !settings['api_key'].trim()) {
      delete settings['api_key'];
    }
    this.stateService.setLoadingLlm(true);

    this.apiService.loadLlmModel(settings).subscribe({
      next: (response) => {
        this.stateService.setLoadingLlm(false);
        if (response.status === 'error') {
          this.errorDialogService.show(response.message || 'Failed to load LLM');
          return;
        }
        this.loadServerVariables();
      },
      error: (error) => {
        console.error('Failed to load LLM:', error);
        this.stateService.setLoadingLlm(false);
        this.errorDialogService.show('Failed to load LLM');
      }
    });
  }

  private showLoadErrorIfNeeded(scope: 'llm' | 'audio', message: string | null): void {
    if (!message) {
      if (scope === 'llm') {
        this.lastShownLlmError = null;
      } else {
        this.lastShownAudioError = null;
      }
      return;
    }

    if (scope === 'llm') {
      if (this.lastShownLlmError === message) return;
      this.lastShownLlmError = message;
    } else {
      if (this.lastShownAudioError === message) return;
      this.lastShownAudioError = message;
    }

    this.errorDialogService.show(message);
  }

}
