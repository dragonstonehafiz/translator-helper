import { Component, ViewChild, ChangeDetectorRef, OnDestroy, OnInit, HostListener } from '@angular/core';
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
import { ApiService, TaskResultResponse } from '../../services/api.service';
import { StateService, TASK_TYPES } from '../../services/state.service';

@Component({
  selector: 'app-transcribe',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    SubsectionComponent, FileUploadComponent, TextFieldComponent,
    TooltipIconComponent, LoadingTextIndicatorComponent,
    PrimaryButtonComponent, DownloadsListComponent, WaveformPlayerComponent
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
  isTranscribing = false;
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
  private pollingInterval?: any;
  private filePollingInterval?: any;

  constructor(
    private cdr: ChangeDetectorRef,
    private apiService: ApiService,
    private stateService: StateService,
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
      alert('Could not access microphone. Please ensure you have granted microphone permissions.');
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
      alert('Failed to load audio file. Please ensure it is a valid audio file.');
      this.transcribeLineState.audioBlob = null;
    }
  }

  async transcribeAudio(): Promise<void> {
    if (!this.transcribeLineState.audioBlob || this.isTranscribing || this.stateService.hasActiveTask()) return;

    try {
      this.isTranscribing = true;
      this.stateService.setTaskState(TASK_TYPES.transcribeLine, {
        status: 'processing',
        result: null,
        message: null,
        progress: null,
        isPolling: true,
      });

      const clippedBlob = await this.lineWaveform.getActiveBlob();
      if (!clippedBlob) {
        this.isTranscribing = false;
        this.stateService.setTaskState(TASK_TYPES.transcribeLine, {
          status: 'error',
          message: 'Failed to get audio blob. Please try again.',
          isPolling: false,
        });
        alert('Failed to get audio blob. Please try again.');
        return;
      }

      const mimeType = clippedBlob.type || this.transcribeLineState.audioBlob!.type;
      const extension = mimeType.includes('wav')
        ? 'wav'
        : (mimeType.includes('webm') ? 'webm' : 'mp4');
      const audioFile = new File([clippedBlob], `recording.${extension}`, { type: mimeType });

      this.apiService.transcribeAudio(audioFile, this.inputLanguage).subscribe({
        next: (response) => {
          if (response.status === 'processing') {
            this.startPolling();
          } else {
            this.isTranscribing = false;
            this.stateService.setTaskState(TASK_TYPES.transcribeLine, {
              status: 'error',
              message: response.message || 'Failed to start transcription.',
              isPolling: false,
            });
          }
        },
        error: (error) => {
          console.error('Transcription request failed:', error);
          alert('Failed to start transcription. Please try again.');
          this.stateService.setTaskState(TASK_TYPES.transcribeLine, {
            status: 'error',
            message: 'Failed to start transcription. Please try again.',
            isPolling: false,
          });
          this.isTranscribing = false;
        }
      });
    } catch (error) {
      console.error('Error starting transcription:', error);
      alert('Failed to start transcription. Please try again.');
      this.stateService.setTaskState(TASK_TYPES.transcribeLine, {
        status: 'error',
        message: 'Failed to start transcription. Please try again.',
        isPolling: false,
      });
      this.isTranscribing = false;
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
        alert('MP3 encoding is not supported in this browser. Downloading WAV instead.');
      }
    } catch (error) {
      console.error('Failed to download clipped audio:', error);
      alert('Failed to download clipped audio. Please try again.');
    }
  }

  private startPolling(): void {
    if (this.pollingInterval) {
      return;
    }
    this.pollingInterval = setInterval(() => {
      this.apiService.getTranscriptionResult(TASK_TYPES.transcribeLine).subscribe({
        next: (response: TaskResultResponse) => {
          this.stateService.setTaskState(TASK_TYPES.transcribeLine, {
            status: response.status,
            result: response.result,
            message: response.message ?? null,
            progress: response.progress ?? null,
            isPolling: response.status === 'processing',
          });
          if (response.status === 'complete' && response.result) {
            this.transcript = response.result.data ?? '';
            this.isTranscribing = false;
            this.stopPolling();
            this.cdr.detectChanges();
          } else if (response.status === 'error') {
            console.error('Transcription error:', response.message);
            alert('Transcription failed: ' + (response.message || 'Unknown error'));
            this.isTranscribing = false;
            this.stopPolling();
          } else if (response.status === 'idle') {
            this.isTranscribing = false;
            this.stopPolling();
          }
        },
        error: (error) => {
          console.error('Polling error:', error);
          this.isTranscribing = false;
          this.stopPolling();
        }
      });
    }, 1000);
  }

  private stopPolling(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = undefined;
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
      alert('Failed to load audio file. Please ensure it is a valid audio file.');
    }
  }

  async transcribeFileAudio(): Promise<void> {
    if (!this.transcribeFileState.audioBlob || this.isTranscribing || this.stateService.hasActiveTask()) return;

    try {
      this.isTranscribing = true;
      this.stateService.setTaskState(TASK_TYPES.transcribeFile, {
        status: 'processing',
        result: null,
        message: null,
        progress: null,
        isPolling: true,
      });
      const filename = this.transcribeFileState.audioFile?.name || 'audio.wav';
      const audioFile = new File([this.transcribeFileState.audioBlob], filename, { type: 'audio/wav' });
      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('language', this.fileInputLanguage);

      this.apiService.transcribeFile(formData).subscribe({
        next: (response) => {
          if (response.status === 'processing') {
            this.startFilePolling();
          } else {
            this.isTranscribing = false;
            this.stateService.setTaskState(TASK_TYPES.transcribeFile, {
              status: 'error',
              message: response.message || 'Failed to start transcription.',
              isPolling: false,
            });
            alert(response.message || 'Failed to start transcription.');
          }
        },
        error: (error) => {
          console.error('Transcribe file request failed:', error);
          alert('Failed to start transcription. Please try again.');
          this.stateService.setTaskState(TASK_TYPES.transcribeFile, {
            status: 'error',
            message: 'Failed to start transcription. Please try again.',
            isPolling: false,
          });
          this.isTranscribing = false;
        }
      });
    } catch (error) {
      console.error('Error starting file transcription:', error);
      this.stateService.setTaskState(TASK_TYPES.transcribeFile, {
        status: 'error',
        message: 'Failed to start transcription. Please try again.',
        isPolling: false,
      });
      this.isTranscribing = false;
    }
  }

  private startFilePolling(): void {
    if (this.filePollingInterval) {
      return;
    }
    this.filePollingInterval = setInterval(() => {
      this.apiService.getTranscriptionResult(TASK_TYPES.transcribeFile).subscribe({
        next: (response: TaskResultResponse) => {
          this.stateService.setTaskState(TASK_TYPES.transcribeFile, {
            status: response.status,
            result: response.result,
            message: response.message ?? null,
            progress: response.progress ?? null,
            isPolling: response.status === 'processing',
          });
          if (response.status === 'complete') {
            this.isTranscribing = false;
            this.stopFilePolling();
            this.refreshFileDownloads();
            this.cdr.detectChanges();
          } else if (response.status === 'error' || response.status === 'idle') {
            this.isTranscribing = false;
            this.stopFilePolling();
          }
        },
        error: (error) => {
          console.error('File polling error:', error);
          this.isTranscribing = false;
          this.stopFilePolling();
        }
      });
    }, 1000);
  }

  private stopFilePolling(): void {
    if (this.filePollingInterval) {
      clearInterval(this.filePollingInterval);
      this.filePollingInterval = undefined;
    }
  }

  refreshFileDownloads(): void {
    this.isFetchingFileDownloads = true;
    this.fileDownloadError = '';
    this.apiService.listFiles('transcribe-sub-files').subscribe({
      next: (response) => {
        this.fileAvailableDownloads = response.status === 'success' ? (response.files || []) : [];
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
    this.apiService.downloadFile('transcribe-sub-files', filename).subscribe({
      next: (blob) => {
        this.triggerDownload(blob, filename);
      },
      error: () => alert('Failed to download file. Please try again.')
    });
  }

  deleteTranscribedFile(filename: string): void {
    if (!filename || this.deletingFileDownload) return;
    if (!window.confirm(`Delete ${filename}? This cannot be undone.`)) return;
    this.deletingFileDownload = filename;
    this.apiService.deleteFile('transcribe-sub-files', filename).subscribe({
      next: () => {
        this.fileAvailableDownloads = this.fileAvailableDownloads.filter(f => f.name !== filename);
        this.deletingFileDownload = '';
      },
      error: () => {
        alert('Failed to delete file. Please try again.');
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

  formatDuration(seconds: number): string {
    const totalSeconds = Math.max(0, seconds || 0);
    const mins = Math.floor(totalSeconds / 60);
    const secs = Math.floor(totalSeconds % 60);
    const ms = Math.floor((totalSeconds - Math.floor(totalSeconds)) * 1000);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }

  ngOnDestroy(): void {
    this.stopPolling();
    this.stopFilePolling();
  }

  isAnyTaskRunning(): boolean {
    return this.stateService.hasActiveTask();
  }

  private restoreTaskState(): void {
    const lineTask = this.stateService.getTaskState(TASK_TYPES.transcribeLine);
    const fileTask = this.stateService.getTaskState(TASK_TYPES.transcribeFile);

    this.transcript = lineTask.result?.data ?? '';
    this.isTranscribing = lineTask.status === 'processing' || fileTask.status === 'processing';

    if (lineTask.status === 'processing' || lineTask.isPolling) {
      this.startPolling();
    }
    if (fileTask.status === 'processing' || fileTask.isPolling) {
      this.startFilePolling();
    }
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
