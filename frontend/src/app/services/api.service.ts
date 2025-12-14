import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) { }

  checkReady(): Observable<{is_ready: boolean, message: string, tavily_ready: boolean, openai_ready: boolean, whisper_ready: boolean}> {
    return this.http.get<{is_ready: boolean, message: string, tavily_ready: boolean, openai_ready: boolean, whisper_ready: boolean}>(`${this.baseUrl}/ready`);
  }

  checkRunning(): Observable<{running_translation: boolean, running_transcription: boolean, loading_whisper_model: boolean, loading_gpt_model: boolean, loading_tavily_api: boolean}> {
    return this.http.get<{running_translation: boolean, running_transcription: boolean, loading_whisper_model: boolean, loading_gpt_model: boolean, loading_tavily_api: boolean}>(`${this.baseUrl}/running`);
  }

  healthCheck(): Observable<{status: string, message: string}> {
    return this.http.get<{status: string, message: string}>(`${this.baseUrl}/health`);
  }

  getDevices(): Observable<{devices: {[key: string]: string}}> {
    return this.http.get<{devices: {[key: string]: string}}>(`${this.baseUrl}/devices`);
  }

  loadWhisperModel(modelName: string, device: string): Observable<{status: string, message: string}> {
    return this.http.post<{status: string, message: string}>(`${this.baseUrl}/load-whisper-model`, {
      model_name: modelName,
      device: device
    });
  }

  loadGptModel(modelName: string, apiKey: string, temperature: number): Observable<{status: string, message: string}> {
    return this.http.post<{status: string, message: string}>(`${this.baseUrl}/load-gpt-model`, {
      model_name: modelName,
      api_key: apiKey,
      temperature: temperature
    });
  }

  loadTavilyApi(apiKey: string): Observable<{status: string, message: string}> {
    return this.http.post<{status: string, message: string}>(`${this.baseUrl}/load-tavily-api`, {
      api_key: apiKey
    });
  }
}
