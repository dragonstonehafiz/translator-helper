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

  loadingWhisper = false;
  loadingGpt = false;

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

  constructor(
    private apiService: ApiService,
    private stateService: StateService
  ) {}

  ngOnInit(): void {
    this.loadSettingsSchema();
    this.loadFromState();

    // Subscribe to loading states
    this.stateService.loadingWhisper$.subscribe(loading => {
      this.loadingWhisper = loading;
    });

    this.stateService.loadingGpt$.subscribe(loading => {
      this.loadingGpt = loading;
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
        this.stateService.setSettingsSchema(schema);
        this.applySchema(schema);
      },
      error: (error) => {
        console.error('Failed to load settings schema:', error);
      }
    });
  }

  loadServerVariables(): void {
    this.apiService.getServerVariables().subscribe({
      next: (response) => {
        const audioVars = Array.isArray(response.audio) ? response.audio : [];
        const llmVars = Array.isArray(response.llm) ? response.llm : [];

        this.stateService.setLlmReady(response.llm_ready);
        this.stateService.setAudioReady(response.audio_ready);
        this.stateService.setReady(response.llm_ready && response.audio_ready);
        this.llmReady = response.llm_ready;
        this.audioReady = response.audio_ready;
        if (response.llm_ready) {
          this.stateService.setLoadingGpt(false);
        }
        if (response.audio_ready) {
          this.stateService.setLoadingWhisper(false);
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
        this.stateService.setLoadingGpt(status.loading_gpt_model);
        this.stateService.setLoadingWhisper(status.loading_whisper_model);
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

  private setSettingsValue(scope: 'audio' | 'llm', key: string, value: string | number | boolean): void {
    this.settingsValues[scope][key] = value;
  }


  loadWhisperModel(): void {
    if (this.loadingWhisper) return;

    const modelName = this.settingsValues.audio['model_name'] as string | undefined;
    const device = this.settingsValues.audio['device'] as string | undefined;

    if (!modelName || !device) {
      alert('Please select a model and device');
      return;
    }

    const settings = { ...this.settingsValues.audio };

    this.apiService.loadWhisperModel(settings).subscribe({
      next: (response) => {
        console.log(response.message);
        this.stateService.setLoadingWhisper(true);
      },
      error: (error) => {
        console.error('Failed to load Whisper model:', error);
        alert('Failed to load Whisper model');
      }
    });
  }

  loadGptModel(): void {
    if (this.loadingGpt) {
      return;
    }

    const apiKey = this.settingsValues.llm['api_key'] as string | undefined;
    const requiredFields = (this.llmSchema?.fields || []).filter(field => field.required && field.key !== 'api_key');
    for (const field of requiredFields) {
      const value = this.settingsValues.llm[field.key];
      if (value === undefined || value === null || (typeof value === 'string' && !value.trim())) {
        alert(`Please enter ${field.label}`);
        return;
      }
    }

    if (this.llmApiKeyRequired && !apiKey && this.llmReady === false) {
      alert('Please enter OpenAI API key');
      return;
    }

    const settings = { ...this.settingsValues.llm };
    if (typeof settings['api_key'] === 'string' && !settings['api_key'].trim()) {
      delete settings['api_key'];
    }

    this.apiService.loadGptModel(settings).subscribe({
      next: (response) => {
        console.log(response.message);
        this.stateService.setLoadingGpt(true);
      },
      error: (error) => {
        console.error('Failed to load GPT model:', error);
        alert('Failed to load GPT model');
      }
    });
  }

}
