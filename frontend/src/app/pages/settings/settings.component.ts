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
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, PrimaryButtonComponent],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit, OnDestroy {
  llmReady: boolean | null = null;
  audioReady: boolean | null = null;

  loadingWhisper = false;
  loadingGpt = false;

  // Current server configuration
  currentWhisperModel = '';
  currentDevice = '';
  currentDeviceLabel = '';
  currentOpenaiModel = '';
  currentTemperature = 0;

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
  private hasInitializedForm = false;

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
    });
  }

  checkStatus(): void {
    this.loadServerVariables();
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
        const audioVars = response.audio;
        const llmVars = response.llm;

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

        this.currentWhisperModel = audioVars.whisper_model;
        this.currentDevice = audioVars.device;
        this.currentOpenaiModel = llmVars.openai_model;
        this.currentTemperature = llmVars.temperature;
        if (!this.hasInitializedForm) {
          if (audioVars.whisper_model) {
            this.setSettingsValue('audio', 'model_name', audioVars.whisper_model);
          }
          if (audioVars.device) {
            this.setSettingsValue('audio', 'device', audioVars.device);
          }
          if (llmVars.openai_model) {
            this.setSettingsValue('llm', 'model_name', llmVars.openai_model);
          }
          if (llmVars.temperature !== undefined && llmVars.temperature !== null) {
            this.setSettingsValue('llm', 'temperature', llmVars.temperature);
          }
          this.hasInitializedForm = true;
        }
        this.stateService.setServerVariables({
          whisperModel: audioVars.whisper_model,
          device: audioVars.device,
          openaiModel: llmVars.openai_model,
          temperature: llmVars.temperature
        });
        this.updateDeviceLabel();
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
    if (serverVars.whisperModel !== null) {
      this.currentWhisperModel = serverVars.whisperModel;
      this.setSettingsValue('audio', 'model_name', serverVars.whisperModel);
    }
    if (serverVars.device !== null) {
      this.currentDevice = serverVars.device;
      this.setSettingsValue('audio', 'device', serverVars.device);
    }
    if (serverVars.openaiModel !== null) {
      this.currentOpenaiModel = serverVars.openaiModel;
      this.setSettingsValue('llm', 'model_name', serverVars.openaiModel);
    }
    if (serverVars.temperature !== null) {
      this.currentTemperature = serverVars.temperature;
      this.setSettingsValue('llm', 'temperature', serverVars.temperature);
    }
    if (
      serverVars.whisperModel !== null ||
      serverVars.device !== null ||
      serverVars.openaiModel !== null ||
      serverVars.temperature !== null
    ) {
      this.hasInitializedForm = true;
    }

    if (llmReady === null || audioReady === null) {
      this.checkStatus();
    }

    this.updateDeviceLabel();
  }

  private applySchema(schema: SettingsSchemaBundle): void {
    this.audioSchema = schema.audio;
    this.llmSchema = schema.llm;
    this.llmApiKeyRequired = Boolean(
      this.llmSchema?.fields.find(field => field.key === 'api_key')?.required
    );

    this.initializeSettingsValues('audio', this.audioSchema);
    this.initializeSettingsValues('llm', this.llmSchema);
    this.updateDeviceLabel();
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

  private updateDeviceLabel(): void {
    if (!this.currentDevice) {
      this.currentDeviceLabel = '';
      return;
    }

    const deviceField = this.audioSchema?.fields.find(field => field.key === 'device');
    const match = deviceField?.options?.find(option => option.value === this.currentDevice);
    this.currentDeviceLabel = match ? match.label : this.currentDevice;
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
    const modelName = this.settingsValues.llm['model_name'] as string | undefined;
    const temperatureValue = this.settingsValues.llm['temperature'] as number | undefined;
    const temperature = temperatureValue !== undefined ? Number(temperatureValue) : this.currentTemperature;

    if (!modelName) {
      alert('Please select an LLM model');
      return;
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
