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
  active_task_type: string | null;
}

export interface ServerVariablesData {
  audio: {key?: string; label?: string; value?: unknown}[];
  llm: {key?: string; label?: string; value?: unknown}[];
  search: {key?: string; label?: string; value?: unknown}[];
  llm_ready: boolean;
  audio_ready: boolean;
  search_ready: boolean;
  llm_loading_error: string | null;
  audio_loading_error: string | null;
  search_loading_error: string | null;
}

export interface SeriesSummary {
  id: string;
  name: string;
  input_lang: string;
  output_lang: string;
  character_count: number;
  glossary_count: number;
}

export interface SeriesCharacter {
  id: string;
  name: string;
  aliases: string[];
  personality: string[];
  relationships: { [character: string]: string[] };
  history: string[];
}

export interface SeriesGlossaryTerm {
  id: string;
  term: string;
  translation: string;
  notes: string;
}

export interface SeriesData {
  id: string;
  name: string;
  input_lang: string;
  output_lang: string;
  notes: string;
  characters: SeriesCharacter[];
  glossary: SeriesGlossaryTerm[];
}

export interface SeriesListData {
  series: SeriesSummary[];
}

export interface LibraryProposals {
  new_characters: Omit<SeriesCharacter, 'id'>[];
  updated_characters: {id: string; field: string; append: string}[];
  new_glossary: Omit<SeriesGlossaryTerm, 'id'>[];
  updated_glossary: {id: string; field: string; value: string}[];
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

  loadSearchModel(settings: Record<string, unknown>): Observable<ApiResponse<null>> {
    return this.http.post<ApiResponse<null>>(`${this.baseUrl}/utils/load-search-model`, {
      provider: 'search',
      settings
    });
  }

  getServerVariables(): Observable<ApiResponse<ServerVariablesData>> {
    return this.http.get<ApiResponse<ServerVariablesData>>(`${this.baseUrl}/utils/server-variables`);
  }

  getTaskResult(taskType: string): Observable<TaskResultResponse> {
    return this.http.get<TaskResultResponse>(`${this.baseUrl}/task-results/${encodeURIComponent(taskType)}`);
  }

  listSeries(): Observable<ApiResponse<SeriesListData>> {
    return this.http.get<ApiResponse<SeriesListData>>(`${this.baseUrl}/library/`);
  }

  createSeries(data: {name: string; input_lang: string; output_lang: string; notes?: string}): Observable<ApiResponse<SeriesData>> {
    return this.http.post<ApiResponse<SeriesData>>(`${this.baseUrl}/library/`, data);
  }

  getSeries(seriesId: string): Observable<ApiResponse<SeriesData>> {
    return this.http.get<ApiResponse<SeriesData>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}`);
  }

  updateSeries(seriesId: string, data: {name?: string; input_lang?: string; output_lang?: string; notes?: string}): Observable<ApiResponse<SeriesData>> {
    return this.http.patch<ApiResponse<SeriesData>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}`, data);
  }

  deleteSeries(seriesId: string): Observable<ApiResponse<null>> {
    return this.http.delete<ApiResponse<null>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}`);
  }

  addCharacter(seriesId: string, data: Omit<SeriesCharacter, 'id'>): Observable<ApiResponse<SeriesData>> {
    return this.http.post<ApiResponse<SeriesData>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}/characters`, data);
  }

  updateCharacter(seriesId: string, characterId: string, data: Partial<Omit<SeriesCharacter, 'id'>>): Observable<ApiResponse<SeriesData>> {
    return this.http.patch<ApiResponse<SeriesData>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}/characters/${encodeURIComponent(characterId)}`, data);
  }

  deleteCharacter(seriesId: string, characterId: string): Observable<ApiResponse<null>> {
    return this.http.delete<ApiResponse<null>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}/characters/${encodeURIComponent(characterId)}`);
  }

  addGlossaryTerm(seriesId: string, data: Omit<SeriesGlossaryTerm, 'id'>): Observable<ApiResponse<SeriesData>> {
    return this.http.post<ApiResponse<SeriesData>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}/glossary`, data);
  }

  updateGlossaryTerm(seriesId: string, termId: string, data: Partial<Omit<SeriesGlossaryTerm, 'id'>>): Observable<ApiResponse<SeriesData>> {
    return this.http.patch<ApiResponse<SeriesData>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}/glossary/${encodeURIComponent(termId)}`, data);
  }

  deleteGlossaryTerm(seriesId: string, termId: string): Observable<ApiResponse<null>> {
    return this.http.delete<ApiResponse<null>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}/glossary/${encodeURIComponent(termId)}`);
  }

  startLibraryUpdate(seriesId: string, file: File): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/library/${encodeURIComponent(seriesId)}/update`, formData);
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

  reviewTranslatedFile(originalFile: File, translatedFile: File, context: any, inputLang: string, outputLang: string, batchSize: number): Observable<ApiResponse<TaskStartData>> {
    const formData = new FormData();
    formData.append('file', originalFile);
    formData.append('translated_file', translatedFile);
    formData.append('context', JSON.stringify(context));
    formData.append('input_lang', inputLang);
    formData.append('output_lang', outputLang);
    formData.append('batch_size', batchSize.toString());
    return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/translate/review-translated-file`, formData);
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

}

export interface TaskResultResponse extends ApiResponse<TaskResultData> {
  status: TaskStatus;
}
