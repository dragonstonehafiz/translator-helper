import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit, OnDestroy {
  tavilyReady = false;
  openaiReady = false;
  whisperReady = false;

  loadingWhisper = false;
  loadingGpt = false;
  loadingTavily = false;

  // Running operations
  runningTranscription = false;
  runningTranslation = false;
  runningContext = false;

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
  tavilyApiKey = '';
  temperature = 0.5;

  // Dropdown options
  whisperModels = ['tiny', 'base', 'small', 'medium', 'large', 'turbo'];
  openaiModels = ['gpt-4.1-mini', 'gpt-4.1', 'gpt-5.1', 'gpt-4o', 'o4-mini'];
  devices: {label: string, value: string}[] = [];

  private pollingSubscription?: Subscription;

  constructor(
    private apiService: ApiService,
    private stateService: StateService
  ) {}

  ngOnInit(): void {
    this.checkReadiness();
    this.loadDevices();
    this.loadServerVariables();
    this.startPolling();

    // Subscribe to loading states
    this.stateService.loadingWhisper$.subscribe(loading => {
      this.loadingWhisper = loading;
    });

    this.stateService.loadingGpt$.subscribe(loading => {
      this.loadingGpt = loading;
    });

    this.stateService.loadingTavily$.subscribe(loading => {
      this.loadingTavily = loading;
    });
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  startPolling(): void {
    // Poll every 2 seconds to check loading status
    this.pollingSubscription = interval(2000).subscribe(() => {
      this.checkRunningStatus();
    });
  }

  stopPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
    }
  }

  checkRunningStatus(): void {
    this.apiService.checkRunning().subscribe({
      next: (response) => {
        this.stateService.setLoadingWhisper(response.loading_whisper_model);
        this.stateService.setLoadingGpt(response.loading_gpt_model);
        this.stateService.setLoadingTavily(response.loading_tavily_api);
        
        // Update running operations
        this.runningTranscription = response.running_transcription;
        this.runningTranslation = response.running_translation;
        this.runningContext = response.running_context;
        
        // After loading completes, check readiness
        if (!response.loading_whisper_model || !response.loading_gpt_model || !response.loading_tavily_api) {
          this.checkReadiness();
        }
      },
      error: (error) => {
        console.error('Failed to check running status:', error);
      }
    });
  }

  checkReadiness(): void {
    this.apiService.checkReady().subscribe({
      next: (response) => {
        this.stateService.setReady(response.is_ready);
        this.tavilyReady = response.tavily_ready;
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
        if (this.devices.length > 0) {
          this.device = this.devices[0].value;
        }
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
      },
      error: (error) => {
        console.error('Failed to load server variables:', error);
      }
    });
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
    if (this.loadingGpt || !this.openaiApiKey) {
      alert('Please enter OpenAI API key');
      return;
    }

    this.apiService.loadGptModel(this.openaiModel, this.openaiApiKey, this.temperature).subscribe({
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

  loadTavilyApi(): void {
    if (this.loadingTavily || !this.tavilyApiKey) {
      alert('Please enter Tavily API key');
      return;
    }

    this.apiService.loadTavilyApi(this.tavilyApiKey).subscribe({
      next: (response) => {
        console.log(response.message);
        this.stateService.setLoadingTavily(true);
      },
      error: (error) => {
        console.error('Failed to load Tavily API:', error);
        alert('Failed to load Tavily API');
      }
    });
  }
}
