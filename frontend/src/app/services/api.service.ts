import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { SettingsSchemaBundle, TaskProgress, TaskResultPayload, TaskStatus } from './state.service';

export interface ApiResponse<TData = unknown> {
  status: string;
  message: string | null;
  data: TData | null;
}

export interface RunningStatusData {
  running_llm: boolean;
  running_audio: boolean;
  loading_audio_model: boolean;
  loading_llm_model: boolean;
}

export interface ServerVariablesData {
  audio: {key?: string; label?: string; value?: unknown}[];
  llm: {key?: string; label?: string; value?: unknown}[];
  llm_ready: boolean;
  audio_ready: boolean;
  llm_loading_error: string | null;
  audio_loading_error: string | null;
}

export interface SubtitleFileInfoData {
  total_lines: string;
  character_count: string;
  average_character_count: string;
}

export interface FileListData {
  files: {name: string, size: number, modified: string}[];
}

export interface TaskStartData {
  task_type: string;
}

export interface TaskResultData {
  task_type: string;
  result: TaskResultPayload | null;
  progress: TaskProgress | null;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) { }

  checkRunning(): Observable<ApiResponse<RunningStatusData>> {
    return this.http.get<ApiResponse<RunningStatusData>>(`${this.baseUrl}/utils/running`);
  }

  getSettingsSchema(): Observable<ApiResponse<SettingsSchemaBundle>> {
    return this.http.get<ApiResponse<SettingsSchemaBundle>>(`${this.baseUrl}/utils/settings-schema`);
  }

  loadAudioModel(settings: Record<string, unknown>): Observable<ApiResponse<null>> {
    return this.http.post<ApiResponse<null>>(`${this.baseUrl}/utils/load-audio-model`, {
      provider: 'audio',
      settings
    });
  }

  loadLlmModel(settings: Record<string, unknown>): Observable<ApiResponse<null>> {
    return this.http.post<ApiResponse<null>>(`${this.baseUrl}/utils/load-llm-model`, {
      provider: 'llm',
      settings
    });
  }

  getServerVariables(): Observable<ApiResponse<ServerVariablesData>> {
    return this.http.get<ApiResponse<ServerVariablesData>>(`${this.baseUrl}/utils/server-variables`);
  }

  getTaskResult(taskType: string): Observable<TaskResultResponse> {
    return this.http.get<TaskResultResponse>(`${this.baseUrl}/task-results/${encodeURIComponent(taskType)}`);
  }

  generateCharacterList(file: File, context: any, inputLang: string, outputLang: string): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/context/generate-character-list`, formData);
  }

  generateSynopsis(file: File, context: any, inputLang: string, outputLang: string): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/context/generate-synopsis`, formData);
  }

  generateSummary(file: File, context: any, inputLang: string, outputLang: string): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/context/generate-high-level-summary`, formData);
  }

  generateRecap(contexts: any[], inputLang: string, outputLang: string): Observable<ApiResponse<TaskStartData>> {
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/context/generate-recap`, {
      contexts: contexts,
      input_lang: inputLang,
      output_lang: outputLang
    });
  }

  transcribeAudio(audioFile: File, language: string): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('language', language);
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/transcribe/transcribe-line`, formData);
  }

  getSubtitleFileInfo(file: File): Observable<ApiResponse<SubtitleFileInfoData>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ApiResponse<SubtitleFileInfoData>>(`${this.baseUrl}/utils/get-subtitle-file-info`, formData);
  }

  transcribeFile(formData: FormData): Observable<ApiResponse<TaskStartData>> {
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/transcribe/transcribe-file`, formData);
  }

  translateLine(text: string, context: any, inputLang: string, outputLang: string): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/translate/translate-line`, formData);
  }

  translateFile(file: File, context: any, inputLang: string, outputLang: string, batchSize: number): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    formData.append('batch_size', batchSize.toString());
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/translate/translate-file`, formData);
  }

  listFiles(folder: string): Observable<ApiResponse<FileListData>> {
    return this.http.get<ApiResponse<FileListData>>(`${this.baseUrl}/file-management/${encodeURIComponent(folder)}`);
  }

  getFileBlob(folder: string, filename: string): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/file-management/${encodeURIComponent(folder)}/${encodeURIComponent(filename)}`, { responseType: 'blob' });
  }

  deleteFile(folder: string, filename: string): Observable<ApiResponse<null>> {
    return this.http.delete<ApiResponse<null>>(`${this.baseUrl}/file-management/${encodeURIComponent(folder)}/${encodeURIComponent(filename)}`);
  }

  saveContext(filename: string, context: object): Observable<ApiResponse<null>> {
    return this.http.post<ApiResponse<null>>(`${this.baseUrl}/context/save`, { filename, context });
  }
}

export interface TaskResultResponse extends ApiResponse<TaskResultData> {
  status: TaskStatus;
}
