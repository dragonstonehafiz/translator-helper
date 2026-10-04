import { Component, ViewChild, ChangeDetectorRef, OnDestroy, OnInit, HostListener } from '@angular/core';
import { Observable, Subscription } from 'rxjs';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { DownloadsListComponent } from '../../components/downloads-list/downloads-list.component';
import { WaveformPlayerComponent } from '../../components/waveform-player/waveform-player.component';
import { TabsComponent } from '../../components/tabs/tabs.component';
import { TabComponent } from '../../components/tabs/tab.component';
import { ApiResponse, ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';
import { ConfirmationService } from '../../services/confirmation.service';
import { ErrorDialogService } from '../../services/error-dialog.service';
import { WORKFLOW_TYPES, WorkflowId, WorkflowStartData, WorkflowState, WorkflowStatus, isTextResult } from '../../shared/workflow-types';

const PAGE_WORKFLOWS: WorkflowId[] = [WORKFLOW_TYPES.transcribeClip, WORKFLOW_TYPES.transcribeFile];

@Component({
  selector: 'app-transcribe',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    SubsectionComponent, FileUploadComponent, TextFieldComponent,
    TooltipIconComponent, LoadingTextIndicatorComponent,
    PrimaryButtonComponent, DownloadsListComponent, WaveformPlayerComponent,
    TabsComponent, TabComponent
  ],
  templateUrl: './transcribe.component.html',
  styleUrl: './transcribe.component.scss'
})
export class TranscribeComponent implements OnInit, OnDestroy {
  @ViewChild('lineWaveform') lineWaveform!: WaveformPlayerComponent;
  @ViewChild('fileWaveform') fileWaveform!: WaveformPlayerComponent;

  // --- Transcribe Line section state ---
  transcribeLineState = {
    audioFile: null as File | null,
    audioBlob: null as Blob | null,
    isRecording: false,
  };

  // --- Transcribe File section state ---
  transcribeFileState = {
    audioFile: null as File | null,
    audioBlob: null as Blob | null,
  };

  // --- Section-level (non-waveform) state ---
  transcript = '';
  inputLanguage = 'ja';
  fileInputLanguage = 'ja';
  languageOptions = [
    { code: 'en', name: 'English' },
    { code: 'ja', name: 'Japanese' },
    { code: 'zh', name: 'Chinese' },
    { code: 'ko', name: 'Korean' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'de', name: 'German' },
    { code: 'it', name: 'Italian' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'ru', name: 'Russian' },
    { code: 'ar', name: 'Arabic' },
    { code: 'hi', name: 'Hindi' },
    { code: 'th', name: 'Thai' },
    { code: 'vi', name: 'Vietnamese' },
    { code: 'id', name: 'Indonesian' },
    { code: 'nl', name: 'Dutch' },
    { code: 'pl', name: 'Polish' },
    { code: 'tr', name: 'Turkish' },
  ];
  fileAvailableDownloads: { name: string; size: number; modified: string }[] = [];
  isFetchingFileDownloads = false;
  fileDownloadError = '';
  deletingFileDownload = '';

  // --- Private implementation details ---
  private mediaRecorder?: MediaRecorder;
  private audioChunks: Blob[] = [];
  /** Workflow whose start request is in flight, before the backend has accepted it. */
  private startingWorkflow: WorkflowId | null = null;
  private lastStatuses: Partial<Record<WorkflowId, WorkflowStatus>> = {};
  private workflowSubscription?: Subscription;

  constructor(
    private cdr: ChangeDetectorRef,
    private apiService: ApiService,
    private stateService: StateService,
    private confirmationService: ConfirmationService,
    private errorDialogService: ErrorDialogService,
  ) {}

  ngOnInit(): void {
    this.restoreTaskState();
    this.refreshFileDownloads();
  }

  @HostListener('window:keydown', ['$event'])
  handleWindowKeydown(event: KeyboardEvent): void {
    if (!this.isSpacebar(event)) return;
    if (this.isEditableTarget(event.target)) return;
    if (!this.lineWaveform?.hasAudio) return;
    event.preventDefault();
    this.lineWaveform.togglePlayback();
  }

  // =========================================================================
  // Transcribe Line methods
  // =========================================================================

  async startRecording(): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false
        }
      });

      this.transcribeLineState.audioFile = null;
      this.transcribeLineState.audioBlob = null;
      this.lineWaveform.clearAudio();

      this.audioChunks = [];

      this.mediaRecorder = new MediaRecorder(stream);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = async () => {
        const mimeType = this.mediaRecorder?.mimeType || 'audio/webm';
        const audioBlob = new Blob(this.audioChunks, { type: mimeType });
        this.transcribeLineState.audioBlob = audioBlob;

        stream.getTracks().forEach(track => track.stop());

        this.lineWaveform.audioBlob = audioBlob;
        this.cdr.detectChanges();
      };

      this.mediaRecorder.start();
      this.transcribeLineState.isRecording = true;

    } catch (error) {
      console.error('Error accessing microphone:', error);
      this.errorDialogService.show('Could not access microphone. Please ensure you have granted microphone permissions.');
    }
  }

  stopRecording(): void {
    this.transcribeLineState.isRecording = false;

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
  }

  async onAudioFileSelected(files: File[]): Promise<void> {
    if (!files || files.length === 0) return;

    try {
      const audioFile = files[0];
      this.transcribeLineState.audioFile = audioFile;
      const audioBlob = new Blob([audioFile], { type: audioFile.type });
      this.transcribeLineState.audioBlob = audioBlob;
      this.lineWaveform.audioBlob = audioBlob;
      this.cdr.detectChanges();
    } catch (error) {
      console.error('Error loading audio file:', error);
      this.errorDialogService.show('Failed to load audio file. Please ensure it is a valid audio file.');
      this.transcribeLineState.audioBlob = null;
    }
  }

  async transcribeAudio(): Promise<void> {
    if (!this.transcribeLineState.audioBlob || this.isAnyTaskRunning()) return;

    this.startingWorkflow = WORKFLOW_TYPES.transcribeClip;
    try {
      const clippedBlob = await this.lineWaveform.getActiveBlob();
      if (!clippedBlob) {
        this.startingWorkflow = null;
        this.errorDialogService.show('Failed to get audio blob. Please try again.');
        return;
      }

      const mimeType = clippedBlob.type || this.transcribeLineState.audioBlob!.type;
      const extension = mimeType.includes('wav')
        ? 'wav'
        : (mimeType.includes('webm') ? 'webm' : 'mp4');
      const audioFile = new File([clippedBlob], `recording.${extension}`, { type: mimeType });
      this.startWorkflow(
        'Transcribing the selected audio clip',
        this.apiService.transcribeAudio(audioFile, this.inputLanguage),
      );
    } catch (error) {
      console.error('Error starting transcription:', error);
      this.startingWorkflow = null;
      this.errorDialogService.show('Failed to start transcription. Please try again.');
    }
  }

  async downloadClippedAudioMp3(): Promise<void> {
    if (!this.transcribeLineState.audioBlob) return;

    try {
      const clippedBlob = await this.lineWaveform.getActiveBlob();
      if (!clippedBlob) return;
      const mp3Result = await this.encodeMp3IfSupported(clippedBlob);
      this.triggerDownload(mp3Result.blob, `recording.${mp3Result.extension}`);
      if (mp3Result.extension !== 'mp3') {
        this.errorDialogService.show({
          title: 'Notice',
          message: 'MP3 encoding is not supported in this browser. Downloading WAV instead.'
        });
      }
    } catch (error) {
      console.error('Failed to download clipped audio:', error);
      this.errorDialogService.show('Failed to download clipped audio. Please try again.');
    }
  }

  // =========================================================================
  // Transcribe File methods
  // =========================================================================

  async onFileAudioSelected(files: File[]): Promise<void> {
    if (!files || files.length === 0) return;

    const audioFile = files[0];
    this.transcribeFileState.audioFile = audioFile;

    try {
      const arrayBuffer = await audioFile.arrayBuffer();
      const audioContext = new AudioContext();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      await audioContext.close();

      const channels: Float32Array[] = [];
      for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
        channels.push(audioBuffer.getChannelData(i));
      }
      this.transcribeFileState.audioBlob = this.encodeWav(channels, audioBuffer.sampleRate);
      this.fileWaveform.audioBlob = this.transcribeFileState.audioBlob;
      this.cdr.detectChanges();
    } catch (error) {
      console.error('Error loading audio file for transcription:', error);
      this.errorDialogService.show('Failed to load audio file. Please ensure it is a valid audio file.');
    }
  }

  async transcribeFileAudio(): Promise<void> {
    if (!this.transcribeFileState.audioBlob || this.isAnyTaskRunning()) return;

    this.startingWorkflow = WORKFLOW_TYPES.transcribeFile;
    const filename = this.transcribeFileState.audioFile?.name || 'audio.wav';
    const audioFile = new File([this.transcribeFileState.audioBlob], filename, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('language', this.fileInputLanguage);
    this.startWorkflow('Transcribing the uploaded audio file', this.apiService.transcribeFile(formData));
  }

  /** Send a start request; once the backend accepts it, StateService polls the returned workflow. */
  private startWorkflow(message: string, request: Observable<ApiResponse<WorkflowStartData>>): void {
    request.subscribe({
      next: (response) => {
        this.startingWorkflow = null;
        if (response.status === 'processing' && response.data) {
          this.stateService.trackWorkflow(response.data.workflow, message);
        } else {
          this.errorDialogService.show(response.message || 'Failed to start transcription.');
        }
      },
      error: (error: unknown) => {
        console.error('Transcription request failed:', error);
        this.startingWorkflow = null;
        this.errorDialogService.show('Failed to start transcription. Please try again.');
      }
    });
  }

  /** React when a transcription finishes: show the clip transcript or refresh the file list. */
  private onWorkflowState(state: WorkflowState): void {
    const previous = this.lastStatuses[state.workflow];
    this.lastStatuses[state.workflow] = state.status;
    if (previous === state.status || state.status !== 'complete') return;

    if (state.workflow === WORKFLOW_TYPES.transcribeClip && isTextResult(state.result)) {
      this.transcript = state.result.text;
    } else {
      this.refreshFileDownloads();
    }
    this.cdr.detectChanges();
  }

  refreshFileDownloads(): void {
    this.isFetchingFileDownloads = true;
    this.fileDownloadError = '';
    this.apiService.listFiles('transcribed').subscribe({
      next: (response) => {
        this.fileAvailableDownloads = response.status === 'success' ? (response.data?.files || []) : [];
        if (response.status !== 'success') this.fileDownloadError = 'Unable to load downloads.';
        this.isFetchingFileDownloads = false;
      },
      error: () => {
        this.fileAvailableDownloads = [];
        this.fileDownloadError = 'Failed to load downloads. Please try again.';
        this.isFetchingFileDownloads = false;
      }
    });
  }

  downloadTranscribedFile(filename: string): void {
    this.apiService.getFileBlob('transcribed', filename).subscribe({
      next: (blob) => {
        this.triggerDownload(blob, filename);
      },
      error: () => this.errorDialogService.show('Failed to download file. Please try again.')
    });
  }

  async deleteTranscribedFile(filename: string): Promise<void> {
    if (!filename || this.deletingFileDownload) return;
    const confirmed = await this.confirmationService.confirm({
      title: 'Confirm Deletion',
      message: `Delete ${filename}? This cannot be undone.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;
    this.deletingFileDownload = filename;
    this.apiService.deleteFile('transcribed', filename).subscribe({
      next: () => {
        this.fileAvailableDownloads = this.fileAvailableDownloads.filter(f => f.name !== filename);
        this.deletingFileDownload = '';
      },
      error: () => {
        this.errorDialogService.show('Failed to delete file. Please try again.');
        this.deletingFileDownload = '';
      }
    });
  }

  // =========================================================================
  // Shared utilities
  // =========================================================================

  private encodeWav(channels: Float32Array[], sampleRate: number): Blob {
    const numChannels = channels.length;
    const numFrames = channels[0]?.length || 0;
    const bytesPerSample = 2;
    const blockAlign = numChannels * bytesPerSample;
    const buffer = new ArrayBuffer(44 + numFrames * blockAlign);
    const view = new DataView(buffer);

    this.writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + numFrames * blockAlign, true);
    this.writeString(view, 8, 'WAVE');
    this.writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);
    this.writeString(view, 36, 'data');
    view.setUint32(40, numFrames * blockAlign, true);

    let offset = 44;
    for (let i = 0; i < numFrames; i++) {
      for (let channel = 0; channel < numChannels; channel++) {
        const sample = Math.max(-1, Math.min(1, channels[channel][i] || 0));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
        offset += 2;
      }
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }

  private async encodeMp3IfSupported(audioBlob: Blob): Promise<{ blob: Blob; extension: 'mp3' | 'wav' }> {
    const mp3Type = 'audio/mpeg';
    if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported(mp3Type)) {
      return { blob: audioBlob, extension: 'wav' };
    }

    const audioContext = new AudioContext();
    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    const destination = audioContext.createMediaStreamDestination();
    source.connect(destination);

    const recorder = new MediaRecorder(destination.stream, { mimeType: mp3Type });
    const chunks: BlobPart[] = [];

    const recordedBlob = await new Promise<Blob>((resolve, reject) => {
      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      recorder.onerror = () => reject(new Error('MP3 recorder error'));
      recorder.onstop = () => resolve(new Blob(chunks, { type: mp3Type }));
      recorder.start();
      source.start();
      source.onended = () => recorder.stop();
    });

    source.disconnect();
    await audioContext.close();

    return { blob: recordedBlob, extension: 'mp3' };
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  private writeString(view: DataView, offset: number, value: string): void {
    for (let i = 0; i < value.length; i++) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
  }

  ngOnDestroy(): void {
    this.workflowSubscription?.unsubscribe();
  }

  get isTranscribing(): boolean {
    return this.startingWorkflow !== null
      || PAGE_WORKFLOWS.some(workflow => this.stateService.getWorkflowState(workflow).status === 'processing');
  }

  isAnyTaskRunning(): boolean {
    return this.startingWorkflow !== null || this.stateService.hasActiveWorkflow();
  }

  private restoreTaskState(): void {
    const clipState = this.stateService.getWorkflowState(WORKFLOW_TYPES.transcribeClip);
    this.transcript = isTextResult(clipState.result) ? clipState.result.text : '';
    for (const workflow of PAGE_WORKFLOWS) {
      this.lastStatuses[workflow] = this.stateService.getWorkflowState(workflow).status;
    }
    this.workflowSubscription = this.stateService.workflowStates$.subscribe(states => {
      for (const workflow of PAGE_WORKFLOWS) {
        const state = states[workflow];
        if (state) this.onWorkflowState(state);
      }
    });
  }

  private isSpacebar(event: KeyboardEvent): boolean {
    return event.code === 'Space' || event.key === ' ';
  }

  private isEditableTarget(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false;
    const tagName = target.tagName;
    if (tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT') return true;
    if (target.isContentEditable) return true;
    const editableAncestor = target.closest?.('[contenteditable="true"]');
    return Boolean(editableAncestor);
  }

}
