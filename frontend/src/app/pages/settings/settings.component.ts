import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';
import { SubsectionComponent } from '../../components/subsection/subsection.component';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit {
  openaiReady = false;
  whisperReady = false;

  loadingWhisper = false;
  loadingGpt = false;


  // Current server configuration
  currentWhisperModel = '';
  currentDevice = '';
  currentOpenaiModel = '';
  currentTemperature = 0;

  // Settings form fields
  whisperModel = 'large';
  device = '';
  openaiModel = 'gpt-4o';
  openaiApiKey = '';
  temperature = 0.5;

  // Dropdown options
  whisperModels = ['tiny', 'base', 'small', 'medium', 'large', 'turbo'];
  openaiModels = ['gpt-4.1-mini', 'gpt-4.1', 'gpt-5.1', 'gpt-4o', 'o4-mini'];
  devices: {label: string, value: string}[] = [];

  constructor(
    private apiService: ApiService,
    private stateService: StateService
  ) {}

  ngOnInit(): void {
    this.loadDevices();
    this.loadFromState();

    // Subscribe to loading states
    this.stateService.loadingWhisper$.subscribe(loading => {
      this.loadingWhisper = loading;
    });

    this.stateService.loadingGpt$.subscribe(loading => {
      this.loadingGpt = loading;
    });

  }

  checkRunningStatus(): void {
    this.apiService.checkRunning().subscribe({
      next: (response) => {
        this.stateService.setLoadingWhisper(response.loading_whisper_model);
        this.stateService.setLoadingGpt(response.loading_gpt_model);
        
        // Update running operations
        
        // After loading completes, check readiness
        if (!response.loading_whisper_model || !response.loading_gpt_model) {
          this.checkReadiness();
        }
      },
      error: (error) => {
        console.error('Failed to check running status:', error);
      }
    });
  }

  checkStatus(): void {
    this.checkRunningStatus();
    this.loadServerVariables();
    this.checkReadiness();
  }

  checkReadiness(): void {
    this.apiService.checkReady().subscribe({
      next: (response) => {
        this.stateService.setReady(response.is_ready);
        this.stateService.setOpenaiReady(response.openai_ready);
        this.stateService.setWhisperReady(response.whisper_ready);
        this.openaiReady = response.openai_ready;
        this.whisperReady = response.whisper_ready;
      },
      error: (error) => {
        console.error('Failed to check readiness:', error);
      }
    });
  }

  loadDevices(): void {
    this.apiService.getDevices().subscribe({
      next: (response) => {
        this.devices = Object.entries(response.devices).map(([label, value]) => ({
          label,
          value
        }));
        if (this.devices.length > 0 && !this.device) {
          this.device = this.devices[0].value;
        }
        this.updateDeviceLabel();
      },
      error: (error) => {
        console.error('Failed to load devices:', error);
      }
    });
  }

  loadServerVariables(): void {
    this.apiService.getServerVariables().subscribe({
      next: (response) => {
        this.currentWhisperModel = response.whisper_model;
        this.currentDevice = response.device;
        this.currentOpenaiModel = response.openai_model;
        this.currentTemperature = response.temperature;
        if (response.whisper_model) {
          this.whisperModel = response.whisper_model;
        }
        if (response.device) {
          this.device = response.device;
        }
        if (response.openai_model) {
          this.openaiModel = response.openai_model;
        }
        if (response.temperature !== undefined && response.temperature !== null) {
          this.temperature = response.temperature;
        }
        this.stateService.setServerVariables({
          whisperModel: response.whisper_model,
          device: response.device,
          openaiModel: response.openai_model,
          temperature: response.temperature
        });
        this.updateDeviceLabel();
      },
      error: (error) => {
        console.error('Failed to load server variables:', error);
      }
    });
  }

  loadFromState(): void {
    const openaiReady = this.stateService.getOpenaiReady();
    const whisperReady = this.stateService.getWhisperReady();
    const serverVars = this.stateService.getServerVariables();

    if (openaiReady !== null) {
      this.openaiReady = openaiReady;
    }
    if (whisperReady !== null) {
      this.whisperReady = whisperReady;
    }
    if (serverVars.whisperModel !== null) {
      this.currentWhisperModel = serverVars.whisperModel;
      this.whisperModel = serverVars.whisperModel;
    }
    if (serverVars.device !== null) {
      this.currentDevice = serverVars.device;
      this.device = serverVars.device;
    }
    if (serverVars.openaiModel !== null) {
      this.currentOpenaiModel = serverVars.openaiModel;
      this.openaiModel = serverVars.openaiModel;
    }
    if (serverVars.temperature !== null) {
      this.currentTemperature = serverVars.temperature;
      this.temperature = serverVars.temperature;
    }

    if (openaiReady === null || whisperReady === null) {
      this.checkStatus();
    }

    this.updateDeviceLabel();
  }

  private updateDeviceLabel(): void {
    const match = this.devices.find(item => item.value === this.currentDevice);
    if (match) {
      this.currentDevice = match.label;
    }
  }

  loadWhisperModel(): void {
    if (this.loadingWhisper) return;

    this.apiService.loadWhisperModel(this.whisperModel, this.device).subscribe({
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

    if (!this.openaiApiKey && !this.openaiReady) {
      alert('Please enter OpenAI API key');
      return;
    }

    const apiKeyToSend = this.openaiApiKey ? this.openaiApiKey : null;

    this.apiService.loadGptModel(this.openaiModel, apiKeyToSend, this.temperature).subscribe({
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
