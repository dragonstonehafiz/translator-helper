import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { SettingsSchemaBundle } from './state.service';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) { }

  checkRunning(): Observable<{running_llm: boolean, running_audio: boolean, loading_audio_model: boolean, loading_llm_model: boolean}> {
    return this.http.get<{running_llm: boolean, running_audio: boolean, loading_audio_model: boolean, loading_llm_model: boolean}>(`${this.baseUrl}/utils/running`);
  }

  getSettingsSchema(): Observable<SettingsSchemaBundle> {
    return this.http.get<SettingsSchemaBundle>(`${this.baseUrl}/utils/settings-schema`);
  }

  loadAudioModel(settings: Record<string, unknown>): Observable<{status: string, message: string}> {
    return this.http.post<{status: string, message: string}>(`${this.baseUrl}/utils/load-audio-model`, {
      provider: 'audio',
      settings
    });
  }

  loadLlmModel(settings: Record<string, unknown>): Observable<{status: string, message: string}> {
    return this.http.post<{status: string, message: string}>(`${this.baseUrl}/utils/load-llm-model`, {
      provider: 'llm',
      settings
    });
  }

  getServerVariables(): Observable<{
    audio: {key?: string; label?: string; value?: unknown}[];
    llm: {key?: string; label?: string; value?: unknown}[];
    llm_ready: boolean;
    audio_ready: boolean;
    llm_loading_error: string | null;
    audio_loading_error: string | null;
  }> {
    return this.http.get<{
      audio: {key?: string; label?: string; value?: unknown}[];
      llm: {key?: string; label?: string; value?: unknown}[];
      llm_ready: boolean;
      audio_ready: boolean;
      llm_loading_error: string | null;
      audio_loading_error: string | null;
    }>(`${this.baseUrl}/utils/server-variables`);
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
    return this.http.post<{status: string, result?: {total_lines: string, character_count: string, average_character_count: string}, message?: string}>(`${this.baseUrl}/utils/get-subtitle-file-info`, formData);
  }

  getTranscriptionResult(): Observable<{status: string, result?: {type: string, data: string}, message?: string}> {
    return this.http.get<{status: string, result?: {type: string, data: string}, message?: string}>(`${this.baseUrl}/transcribe/result`);
  }

  transcribeFile(formData: FormData): Observable<{status: string, message?: string}> {
    return this.http.post<{status: string, message?: string}>(`${this.baseUrl}/transcribe/transcribe-file`, formData);
  }

  translateLine(text: string, context: any, inputLang: string, outputLang: string): Observable<{status: string, message?: string}> {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<{status: string, message?: string}>(`${this.baseUrl}/translate/translate-line`, formData);
  }

  translateFile(file: File, context: any, inputLang: string, outputLang: string, batchSize: number): Observable<{status: string, message?: string}> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    formData.append('batch_size', batchSize.toString());
    return this.http.post<{status: string, message?: string}>(`${this.baseUrl}/translate/translate-file`, formData);
  }

  getTranslationResult(): Observable<{status: string, result?: {type: string, data: string, filename?: string}, message?: string}> {
    return this.http.get<{status: string, result?: {type: string, data: string, filename?: string}, message?: string}>(`${this.baseUrl}/translate/result`);
  }

  listFiles(folder: string): Observable<{status: string, files: {name: string, size: number, modified: string}[]}> {
    return this.http.get<{status: string, files: {name: string, size: number, modified: string}[]}>(`${this.baseUrl}/file-management/${encodeURIComponent(folder)}`);
  }

  downloadFile(folder: string, filename: string): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/file-management/${encodeURIComponent(folder)}/${encodeURIComponent(filename)}`, { responseType: 'blob' });
  }

  deleteFile(folder: string, filename: string): Observable<{status: string}> {
    return this.http.delete<{status: string}>(`${this.baseUrl}/file-management/${encodeURIComponent(folder)}/${encodeURIComponent(filename)}`);
  }

  saveContext(filename: string, context: object): Observable<{status: string}> {
    return this.http.post<{status: string}>(`${this.baseUrl}/context/save`, { filename, context });
  }
}
