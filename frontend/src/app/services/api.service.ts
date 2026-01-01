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

  checkRunning(): Observable<{running_translation: boolean, running_transcription: boolean, running_context: boolean, loading_whisper_model: boolean, loading_gpt_model: boolean, loading_tavily_api: boolean}> {
    return this.http.get<{running_translation: boolean, running_transcription: boolean, running_context: boolean, loading_whisper_model: boolean, loading_gpt_model: boolean, loading_tavily_api: boolean}>(`${this.baseUrl}/running`);
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

  loadGptModel(modelName: string, apiKey: string | null, temperature: number): Observable<{status: string, message: string}> {
    const payload: { model_name: string; temperature: number; api_key?: string | null } = {
      model_name: modelName,
      temperature: temperature
    };

    if (apiKey) {
      payload.api_key = apiKey;
    }

    return this.http.post<{status: string, message: string}>(`${this.baseUrl}/load-gpt-model`, payload);
  }

  loadTavilyApi(apiKey: string): Observable<{status: string, message: string}> {
    return this.http.post<{status: string, message: string}>(`${this.baseUrl}/load-tavily-api`, {
      api_key: apiKey
    });
  }

  getServerVariables(): Observable<{whisper_model: string, device: string, openai_model: string, temperature: number}> {
    return this.http.get<{whisper_model: string, device: string, openai_model: string, temperature: number}>(`${this.baseUrl}/server/variables`);
  }

  generateWebContext(seriesName: string, keywords: string, inputLang: string, outputLang: string): Observable<{status: string, context?: string, message?: string}> {
    return this.http.post<{status: string, context?: string, message?: string}>(`${this.baseUrl}/context/generate-web-context`, {
      series_name: seriesName,
      keywords: keywords,
      input_lang: inputLang,
      output_lang: outputLang
    });
  }

  getContextResult(): Observable<{status: string, result?: {type: string, data: string}, message?: string}> {
    return this.http.get<{status: string, result?: {type: string, data: string}, message?: string}>(`${this.baseUrl}/context/result`);
  }

  generateCharacterList(file: File, context: any, inputLang: string, outputLang: string): Observable<{status: string, character_list?: string, message?: string}> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<{status: string, character_list?: string, message?: string}>(`${this.baseUrl}/context/generate-character-list`, formData);
  }

  generateSynopsis(file: File, context: any, inputLang: string, outputLang: string): Observable<{status: string, synopsis?: string, message?: string}> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<{status: string, synopsis?: string, message?: string}>(`${this.baseUrl}/context/generate-synopsis`, formData);
  }

  generateSummary(file: File, context: any, inputLang: string, outputLang: string): Observable<{status: string, summary?: string, message?: string}> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<{status: string, summary?: string, message?: string}>(`${this.baseUrl}/context/generate-high-level-summary`, formData);
  }

  generateRecap(contexts: any[], inputLang: string, outputLang: string): Observable<{status: string, recap?: string, message?: string}> {
    return this.http.post<{status: string, recap?: string, message?: string}>(`${this.baseUrl}/context/generate-recap`, {
      contexts: contexts,
      input_lang: inputLang,
      output_lang: outputLang
    });
  }

  transcribeAudio(audioFile: File, language: string): Observable<{status: string, message?: string}> {
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('language', language);
    return this.http.post<{status: string, message?: string}>(`${this.baseUrl}/transcribe/transcribe-line`, formData);
  }

  getTranscribeFileInfo(file: File): Observable<{status: string, result?: {total_lines: string, character_count: string, average_character_count: string}, message?: string}> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{status: string, result?: {total_lines: string, character_count: string, average_character_count: string}, message?: string}>(`${this.baseUrl}/transcribe/get-file-info/`, formData);
  }

  getTranscriptionResult(): Observable<{status: string, result?: {type: string, data: string}, message?: string}> {
    return this.http.get<{status: string, result?: {type: string, data: string}, message?: string}>(`${this.baseUrl}/transcribe/result`);
  }

  translateLine(text: string, context: any, inputLang: string, outputLang: string): Observable<{status: string, message?: string}> {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<{status: string, message?: string}>(`${this.baseUrl}/translate/translate-line`, formData);
  }

  translateFile(file: File, context: any, inputLang: string, outputLang: string, contextWindow: number): Observable<{status: string, message?: string}> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    formData.append('context_window', contextWindow.toString());
    return this.http.post<{status: string, message?: string}>(`${this.baseUrl}/translate/translate-file`, formData);
  }

  getTranslationResult(): Observable<{status: string, result?: {type: string, data: string, filename?: string}, message?: string}> {
    return this.http.get<{status: string, result?: {type: string, data: string, filename?: string}, message?: string}>(`${this.baseUrl}/translate/result`);
  }
}
