import { Component, ViewChild, ElementRef, AfterViewInit, ChangeDetectorRef, OnDestroy, OnInit, HostListener } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { PrimaryButtonComponent } from '../../components/primary-button/primary-button.component';
import { DownloadsListComponent } from '../../components/downloads-list/downloads-list.component';
import { ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';

@Component({
  selector: 'app-transcribe',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    SubsectionComponent, FileUploadComponent, TextFieldComponent,
    TooltipIconComponent, LoadingTextIndicatorComponent,
    PrimaryButtonComponent, DownloadsListComponent
  ],
  templateUrl: './transcribe.component.html',
  styleUrl: './transcribe.component.scss'
})
export class TranscribeComponent implements AfterViewInit, OnInit, OnDestroy {
  @ViewChild('waveformCanvas') waveformCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('audioPlayer') audioPlayer?: ElementRef<HTMLAudioElement>;
  @ViewChild('fileWaveformCanvas') fileWaveformCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('fileAudioPlayer') fileAudioPlayer?: ElementRef<HTMLAudioElement>;

  // --- Transcribe Line section state ---
  transcribeLineState = {
    audioFile: null as File | null,
    audioUrl: null as string | null,
    audioBlob: null as Blob | null,
    decodedBuffer: null as AudioBuffer | null,
    channelData: null as Float32Array | null,
    progress: 0,
    playbackTime: 0,
    playbackDuration: 0,
    recordedDuration: 0,
    isPlaying: false,
    isRecording: false,
    recordingDuration: 0,
    selectionStart: 0,
    selectionEnd: 0,
  };

  // --- Transcribe File section state ---
  transcribeFileState = {
    audioFile: null as File | null,
    audioUrl: null as string | null,
    audioBlob: null as Blob | null,
    channelData: null as Float32Array | null,
    progress: 0,
    playbackTime: 0,
    playbackDuration: 0,
    isPlaying: false,
  };

  // --- Section-level (non-waveform) state ---
  translateLineCollapsed = true;
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
  isTranscribingFile = false;
  fileAvailableDownloads: { name: string; size: number; modified: string }[] = [];
  isFetchingFileDownloads = false;
  fileDownloadError = '';
  deletingFileDownload = '';

  // --- Private implementation details ---
  private isSelecting = false;
  private selectionDragMode: 'new' | 'start' | 'end' = 'new';
  private ignoreNextClick = false;
  private playbackRafId: number | null = null;
  private recordingRafId: number | null = null;
  private recordingStartTime = 0;
  private mediaRecorder?: MediaRecorder;
  private audioChunks: Blob[] = [];
  private pollingInterval?: any;
  private filePollingInterval?: any;

  constructor(
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer,
    private apiService: ApiService,
    private stateService: StateService
  ) {}

  ngOnInit(): void {
    this.refreshFileDownloads();
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.drawWaveform(true), 100);

    if (this.audioPlayer) {
      const audio = this.audioPlayer.nativeElement;
      audio.addEventListener('timeupdate', () => {
        if (audio.duration) {
          this.transcribeLineState.progress = audio.currentTime / audio.duration;
          this.redrawWaveformWithProgress();
        }
        this.transcribeLineState.playbackTime = audio.currentTime || 0;
        if (this.hasSelection() && audio.currentTime >= this.transcribeLineState.selectionEnd) {
          audio.pause();
          audio.currentTime = this.transcribeLineState.selectionEnd;
        }
      });
      audio.addEventListener('loadedmetadata', () => {
        this.transcribeLineState.playbackDuration = Number.isFinite(audio.duration) ? audio.duration : 0;
        this.transcribeLineState.recordedDuration = this.transcribeLineState.playbackDuration || this.transcribeLineState.recordedDuration;
        if (this.transcribeLineState.playbackDuration > 0) {
          this.transcribeLineState.selectionStart = 0;
          this.transcribeLineState.selectionEnd = this.transcribeLineState.playbackDuration;
          this.redrawWaveformWithProgress();
        }
      });
      audio.addEventListener('play', () => {
        this.transcribeLineState.isPlaying = true;
        this.startPlaybackLoop();
      });
      audio.addEventListener('pause', () => {
        this.transcribeLineState.isPlaying = false;
        this.stopPlaybackLoop();
      });
      audio.addEventListener('ended', () => {
        this.transcribeLineState.isPlaying = false;
        this.stopPlaybackLoop();
      });
    }

    if (this.fileAudioPlayer) {
      const fileAudio = this.fileAudioPlayer.nativeElement;
      fileAudio.addEventListener('timeupdate', () => {
        if (fileAudio.duration) {
          this.transcribeFileState.progress = fileAudio.currentTime / fileAudio.duration;
          this.redrawFileWaveformWithProgress();
        }
        this.transcribeFileState.playbackTime = fileAudio.currentTime || 0;
        this.cdr.detectChanges();
      });
      fileAudio.addEventListener('loadedmetadata', () => {
        this.transcribeFileState.playbackDuration = Number.isFinite(fileAudio.duration) ? fileAudio.duration : 0;
      });
      fileAudio.addEventListener('play', () => {
        this.transcribeFileState.isPlaying = true;
        this.cdr.detectChanges();
      });
      fileAudio.addEventListener('pause', () => {
        this.transcribeFileState.isPlaying = false;
        this.cdr.detectChanges();
      });
      fileAudio.addEventListener('ended', () => {
        this.transcribeFileState.isPlaying = false;
        this.transcribeFileState.progress = 0;
        this.cdr.detectChanges();
      });
    }

    if (this.waveformCanvas) {
      const canvas = this.waveformCanvas.nativeElement;
      canvas.addEventListener('click', (event) => this.handleWaveformClick(event));
      canvas.addEventListener('mousedown', (event) => this.handleWaveformMouseDown(event));
      canvas.addEventListener('mousemove', (event) => this.handleWaveformMouseMove(event));
      canvas.addEventListener('mouseup', () => this.handleWaveformMouseUp());
      canvas.addEventListener('mouseleave', () => this.handleWaveformMouseUp());
      this.waveformCanvas.nativeElement.style.cursor = 'pointer';
    }
  }

  @HostListener('window:keydown', ['$event'])
  handleWindowKeydown(event: KeyboardEvent): void {
    if (!this.isSpacebar(event)) return;
    if (this.isEditableTarget(event.target)) return;
    if (!this.transcribeLineState.audioUrl) return;
    event.preventDefault();
    this.togglePlayback();
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

      if (this.transcribeLineState.audioUrl) {
        URL.revokeObjectURL(this.transcribeLineState.audioUrl);
        this.transcribeLineState.audioUrl = null;
        this.transcribeLineState.audioBlob = null;
      }
      this.transcribeLineState.decodedBuffer = null;

      this.drawWaveform(true);
      this.transcribeLineState.recordedDuration = 0;
      this.transcribeLineState.selectionStart = 0;
      this.transcribeLineState.selectionEnd = 0;

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
        this.transcribeLineState.audioUrl = URL.createObjectURL(audioBlob);

        stream.getTracks().forEach(track => track.stop());

        await this.drawWaveformFromAudio(audioBlob);
        if (this.audioPlayer?.nativeElement) {
          this.audioPlayer.nativeElement.currentTime = 0;
        }

        this.cdr.detectChanges();
      };

      this.mediaRecorder.start();
      this.transcribeLineState.isRecording = true;
      this.transcribeLineState.recordingDuration = 0;
      this.transcribeLineState.playbackTime = 0;
      this.transcribeLineState.playbackDuration = 0;
      this.recordingStartTime = performance.now();
      this.startRecordingLoop();

    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please ensure you have granted microphone permissions.');
    }
  }

  stopRecording(): void {
    this.transcribeLineState.isRecording = false;
    this.transcribeLineState.recordedDuration = this.transcribeLineState.recordingDuration;
    this.transcribeLineState.playbackDuration = this.transcribeLineState.recordedDuration;
    this.transcribeLineState.selectionStart = 0;
    this.transcribeLineState.selectionEnd = this.transcribeLineState.playbackDuration;
    this.stopRecordingLoop();

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
  }

  async onAudioFileSelected(files: File[]): Promise<void> {
    if (!files || files.length === 0) return;

    const audioFile = files[0];
    this.transcribeLineState.audioFile = audioFile;

    try {
      if (this.transcribeLineState.audioUrl) {
        URL.revokeObjectURL(this.transcribeLineState.audioUrl);
      }
      if (this.audioPlayer?.nativeElement) {
        this.audioPlayer.nativeElement.pause();
      }

      const audioBlob = new Blob([audioFile], { type: audioFile.type });
      this.transcribeLineState.audioBlob = audioBlob;
      this.transcribeLineState.audioUrl = URL.createObjectURL(audioBlob);
      this.transcribeLineState.decodedBuffer = null;

      await this.drawWaveformFromAudio(audioBlob);

      if (this.audioPlayer?.nativeElement) {
        this.audioPlayer.nativeElement.currentTime = 0;
      }

      this.cdr.detectChanges();
    } catch (error) {
      console.error('Error loading audio file:', error);
      alert('Failed to load audio file. Please ensure it is a valid audio file.');
      this.transcribeLineState.audioFile = null;
    }
  }

  private drawWaveform(silent: boolean = false): void {
    if (!this.waveformCanvas) return;

    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerY = height / 2;

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();
  }

  private async drawWaveformFromAudio(audioBlob: Blob): Promise<void> {
    if (!this.waveformCanvas) return;

    try {
      const canvas = this.waveformCanvas.nativeElement;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const arrayBuffer = await audioBlob.arrayBuffer();
      const audioContext = new AudioContext();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      this.transcribeLineState.decodedBuffer = audioBuffer;

      const channelData = audioBuffer.getChannelData(0);
      this.transcribeLineState.channelData = channelData;
      this.transcribeLineState.playbackDuration = audioBuffer.duration;
      this.transcribeLineState.recordedDuration = audioBuffer.duration;
      this.transcribeLineState.selectionStart = 0;
      this.transcribeLineState.selectionEnd = audioBuffer.duration;

      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);
      ctx.strokeStyle = '#667eea';
      ctx.lineWidth = 2;
      ctx.beginPath();

      const samples = Math.min(width, channelData.length);
      const step = width / samples;
      const blockSize = Math.floor(channelData.length / samples);

      for (let i = 0; i < samples; i++) {
        let sum = 0;
        for (let j = 0; j < blockSize; j++) {
          sum += Math.abs(channelData[i * blockSize + j]);
        }
        const average = sum / blockSize;

        const x = i * step;
        const amplitude = average * height * 0.8;
        const y = centerY + (i % 2 === 0 ? amplitude : -amplitude);

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();
      this.drawSelectionOverlay(ctx, width, height);

      await audioContext.close();
    } catch (error) {
      console.error('Error drawing waveform:', error);
      this.drawWaveform(true);
    }
  }

  private redrawWaveformWithProgress(): void {
    if (!this.waveformCanvas || !this.transcribeLineState.channelData) return;

    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerY = height / 2;

    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const samples = Math.min(width, this.transcribeLineState.channelData.length);
    const step = width / samples;
    const blockSize = Math.floor(this.transcribeLineState.channelData.length / samples);

    for (let i = 0; i < samples; i++) {
      let sum = 0;
      for (let j = 0; j < blockSize; j++) {
        sum += Math.abs(this.transcribeLineState.channelData[i * blockSize + j]);
      }
      const average = sum / blockSize;

      const x = i * step;
      const amplitude = average * height * 0.8;
      const y = centerY + (i % 2 === 0 ? amplitude : -amplitude);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }

    ctx.stroke();
    this.drawSelectionOverlay(ctx, width, height);

    if (this.transcribeLineState.progress > 0) {
      const progressX = this.transcribeLineState.progress * width;
      ctx.strokeStyle = '#ff6b6b';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(progressX, 0);
      ctx.lineTo(progressX, height);
      ctx.stroke();
    }
  }

  private handleWaveformClick(event: MouseEvent): void {
    if (this.ignoreNextClick) {
      this.ignoreNextClick = false;
      return;
    }
    if (!this.waveformCanvas || !this.audioPlayer || !this.transcribeLineState.audioUrl) return;

    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;

    const seekPercent = x / width;
    const audio = this.audioPlayer.nativeElement;

    if (audio.duration) {
      let targetTime = seekPercent * audio.duration;
      if (this.hasSelection()) {
        targetTime = Math.min(Math.max(targetTime, this.transcribeLineState.selectionStart), this.transcribeLineState.selectionEnd);
      }
      audio.currentTime = targetTime;
    }
  }

  private handleWaveformMouseDown(event: MouseEvent): void {
    if (!this.waveformCanvas || !this.transcribeLineState.playbackDuration || !this.transcribeLineState.audioUrl) return;
    this.ignoreNextClick = true;
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;
    const time = (x / width) * this.transcribeLineState.playbackDuration;

    const startX = (this.transcribeLineState.selectionStart / this.transcribeLineState.playbackDuration) * width;
    const endX = (this.transcribeLineState.selectionEnd / this.transcribeLineState.playbackDuration) * width;
    const handleThreshold = 8;

    if (Math.abs(x - startX) <= handleThreshold) {
      this.selectionDragMode = 'start';
    } else if (Math.abs(x - endX) <= handleThreshold) {
      this.selectionDragMode = 'end';
    } else {
      this.selectionDragMode = 'new';
      this.transcribeLineState.selectionStart = time;
      this.transcribeLineState.selectionEnd = time;
    }

    this.isSelecting = true;
    this.updateSelection(time);
  }

  private handleWaveformMouseMove(event: MouseEvent): void {
    if (!this.isSelecting || !this.waveformCanvas || !this.transcribeLineState.playbackDuration) return;
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;
    const time = (x / width) * this.transcribeLineState.playbackDuration;
    this.updateSelection(time);
  }

  private handleWaveformMouseUp(): void {
    if (!this.isSelecting) return;
    this.isSelecting = false;
    if (this.transcribeLineState.selectionEnd < this.transcribeLineState.selectionStart) {
      const temp = this.transcribeLineState.selectionStart;
      this.transcribeLineState.selectionStart = this.transcribeLineState.selectionEnd;
      this.transcribeLineState.selectionEnd = temp;
    }
    this.redrawWaveformWithProgress();
  }

  private updateSelection(time: number): void {
    const clamped = Math.max(0, Math.min(time, this.transcribeLineState.playbackDuration));
    if (this.selectionDragMode === 'start') {
      this.transcribeLineState.selectionStart = clamped;
    } else if (this.selectionDragMode === 'end') {
      this.transcribeLineState.selectionEnd = clamped;
    } else {
      this.transcribeLineState.selectionEnd = clamped;
    }
    if (this.transcribeLineState.selectionEnd < this.transcribeLineState.selectionStart) {
      const temp = this.transcribeLineState.selectionStart;
      this.transcribeLineState.selectionStart = this.transcribeLineState.selectionEnd;
      this.transcribeLineState.selectionEnd = temp;
    }
    this.redrawWaveformWithProgress();
  }

  private hasSelection(): boolean {
    return this.transcribeLineState.playbackDuration > 0 && this.transcribeLineState.selectionEnd > this.transcribeLineState.selectionStart;
  }

  private drawSelectionOverlay(ctx: CanvasRenderingContext2D, width: number, height: number): void {
    if (!this.hasSelection()) return;
    const startX = (this.transcribeLineState.selectionStart / this.transcribeLineState.playbackDuration) * width;
    const endX = (this.transcribeLineState.selectionEnd / this.transcribeLineState.playbackDuration) * width;

    ctx.fillStyle = 'rgba(0, 0, 0, 0.18)';
    ctx.fillRect(0, 0, startX, height);
    ctx.fillRect(endX, 0, width - endX, height);

    ctx.strokeStyle = '#18a0fb';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(startX, 0);
    ctx.lineTo(startX, height);
    ctx.moveTo(endX, 0);
    ctx.lineTo(endX, height);
    ctx.stroke();
  }

  playRecording(): void {
    if (!this.audioPlayer || !this.transcribeLineState.audioUrl) return;
    const audio = this.audioPlayer.nativeElement;
    audio.play();
  }

  togglePlayback(): void {
    if (!this.audioPlayer || !this.transcribeLineState.audioUrl) return;
    const audio = this.audioPlayer.nativeElement;
    if (audio.paused) {
      if (this.hasSelection()) {
        audio.currentTime = this.transcribeLineState.selectionStart;
      } else {
        audio.currentTime = 0;
      }
      audio.play();
    } else {
      audio.pause();
    }
  }

  private startPlaybackLoop(): void {
    if (!this.audioPlayer) return;
    if (this.playbackRafId !== null) return;
    const audio = this.audioPlayer.nativeElement;
    const tick = () => {
      if (!audio.paused && audio.duration) {
        if (this.hasSelection()) {
          const end = this.transcribeLineState.selectionEnd;
          if (audio.currentTime >= end - 0.005) {
            audio.currentTime = end;
            audio.pause();
            this.transcribeLineState.playbackTime = end;
            this.transcribeLineState.progress = end / audio.duration;
            this.redrawWaveformWithProgress();
            this.stopPlaybackLoop();
            return;
          }
        }
        this.transcribeLineState.progress = audio.currentTime / audio.duration;
        this.transcribeLineState.playbackTime = audio.currentTime || 0;
        this.redrawWaveformWithProgress();
        this.playbackRafId = requestAnimationFrame(tick);
      } else {
        this.stopPlaybackLoop();
      }
    };
    this.playbackRafId = requestAnimationFrame(tick);
  }

  private stopPlaybackLoop(): void {
    if (this.playbackRafId === null) return;
    cancelAnimationFrame(this.playbackRafId);
    this.playbackRafId = null;
  }

  private startRecordingLoop(): void {
    if (this.recordingRafId !== null) return;
    const tick = () => {
      if (!this.transcribeLineState.isRecording) {
        this.stopRecordingLoop();
        return;
      }
      this.transcribeLineState.recordingDuration = (performance.now() - this.recordingStartTime) / 1000;
      this.recordingRafId = requestAnimationFrame(tick);
    };
    this.recordingRafId = requestAnimationFrame(tick);
  }

  private stopRecordingLoop(): void {
    if (this.recordingRafId === null) return;
    cancelAnimationFrame(this.recordingRafId);
    this.recordingRafId = null;
  }

  async transcribeAudio(): Promise<void> {
    if (!this.transcribeLineState.audioBlob || this.isTranscribing) return;

    try {
      this.isTranscribing = true;

      const clippedBlob = await this.getClippedAudioBlob();
      const mimeType = clippedBlob.type || this.transcribeLineState.audioBlob.type;
      const extension = mimeType.includes('wav')
        ? 'wav'
        : (mimeType.includes('webm') ? 'webm' : 'mp4');
      const audioFile = new File([clippedBlob], `recording.${extension}`, { type: mimeType });

      this.apiService.transcribeAudio(audioFile, this.inputLanguage).subscribe({
        next: (response) => {
          if (response.status === 'processing') {
            this.startPolling();
          }
        },
        error: (error) => {
          console.error('Transcription request failed:', error);
          alert('Failed to start transcription. Please try again.');
          this.isTranscribing = false;
        }
      });
    } catch (error) {
      console.error('Error starting transcription:', error);
      alert('Failed to start transcription. Please try again.');
      this.isTranscribing = false;
    }
  }

  async downloadClippedAudioMp3(): Promise<void> {
    if (!this.transcribeLineState.audioBlob) return;
    if (this.audioPlayer?.nativeElement) {
      this.audioPlayer.nativeElement.pause();
    }

    try {
      const clippedBlob = await this.getClippedAudioBlob();
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
    this.pollingInterval = setInterval(() => {
      this.apiService.getTranscriptionResult().subscribe({
        next: (response) => {
          if (response.status === 'complete' && response.result) {
            this.transcript = response.result.data;
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

  getDisplayCurrentTime(): number {
    if (this.transcribeLineState.isRecording) {
      return 0;
    }
    if (this.transcribeLineState.playbackDuration > 0 && this.transcribeLineState.selectionEnd > this.transcribeLineState.selectionStart) {
      return Math.max(0, this.transcribeLineState.playbackTime - this.transcribeLineState.selectionStart);
    }
    return this.transcribeLineState.playbackTime;
  }

  getDisplayTotalTime(): number {
    if (this.transcribeLineState.isRecording) {
      return this.transcribeLineState.recordingDuration;
    }
    if (this.transcribeLineState.playbackDuration > 0 && this.transcribeLineState.selectionEnd > this.transcribeLineState.selectionStart) {
      return Math.max(0, this.transcribeLineState.selectionEnd - this.transcribeLineState.selectionStart);
    }
    return this.transcribeLineState.playbackDuration || this.transcribeLineState.recordedDuration;
  }

  private async getClippedAudioBlob(): Promise<Blob> {
    if (!this.transcribeLineState.audioBlob) {
      throw new Error('No recording available');
    }

    const duration = this.transcribeLineState.playbackDuration || this.transcribeLineState.recordedDuration;
    if (!this.hasSelection() || this.isFullSelection(duration)) {
      return this.transcribeLineState.audioBlob;
    }

    const audioBuffer = await this.getDecodedAudioBuffer();
    const sampleRate = audioBuffer.sampleRate;
    const startSample = Math.floor(this.transcribeLineState.selectionStart * sampleRate);
    const endSample = Math.floor(this.transcribeLineState.selectionEnd * sampleRate);
    const safeEnd = Math.max(startSample + 1, Math.min(endSample, audioBuffer.length));
    const numChannels = audioBuffer.numberOfChannels;
    const channels: Float32Array[] = [];

    for (let channel = 0; channel < numChannels; channel++) {
      const channelData = audioBuffer.getChannelData(channel);
      channels.push(channelData.slice(startSample, safeEnd));
    }

    return this.encodeWav(channels, sampleRate);
  }

  private async getDecodedAudioBuffer(): Promise<AudioBuffer> {
    if (this.transcribeLineState.decodedBuffer) {
      return this.transcribeLineState.decodedBuffer;
    }
    if (!this.transcribeLineState.audioBlob) {
      throw new Error('No recording available');
    }
    const arrayBuffer = await this.transcribeLineState.audioBlob.arrayBuffer();
    const audioContext = new AudioContext();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    await audioContext.close();
    this.transcribeLineState.decodedBuffer = audioBuffer;
    return audioBuffer;
  }

  private isFullSelection(duration: number): boolean {
    if (!duration) return true;
    const epsilon = 0.01;
    return Math.abs(this.transcribeLineState.selectionStart) <= epsilon && Math.abs(this.transcribeLineState.selectionEnd - duration) <= epsilon;
  }

  // =========================================================================
  // Transcribe File methods
  // =========================================================================

  async onFileAudioSelected(files: File[]): Promise<void> {
    if (!files || files.length === 0) return;

    const audioFile = files[0];
    this.transcribeFileState.audioFile = audioFile;

    try {
      if (this.transcribeFileState.audioUrl) {
        URL.revokeObjectURL(this.transcribeFileState.audioUrl);
      }
      if (this.fileAudioPlayer?.nativeElement) {
        this.fileAudioPlayer.nativeElement.pause();
      }

      const arrayBuffer = await audioFile.arrayBuffer();
      const audioContext = new AudioContext();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      await audioContext.close();

      this.transcribeFileState.channelData = audioBuffer.getChannelData(0);
      this.transcribeFileState.playbackDuration = audioBuffer.duration;
      this.transcribeFileState.playbackTime = 0;
      this.transcribeFileState.progress = 0;

      const channels: Float32Array[] = [];
      for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
        channels.push(audioBuffer.getChannelData(i));
      }
      this.transcribeFileState.audioBlob = this.encodeWav(channels, audioBuffer.sampleRate);
      this.transcribeFileState.audioUrl = URL.createObjectURL(this.transcribeFileState.audioBlob);

      this.drawFileWaveform();

      if (this.fileAudioPlayer?.nativeElement) {
        this.fileAudioPlayer.nativeElement.currentTime = 0;
      }
      this.cdr.detectChanges();
    } catch (error) {
      console.error('Error loading audio file for transcription:', error);
      alert('Failed to load audio file. Please ensure it is a valid audio file.');
      this.transcribeFileState.audioFile = null;
    }
  }

  private drawFileWaveform(): void {
    if (!this.fileWaveformCanvas || !this.transcribeFileState.channelData) return;

    const canvas = this.fileWaveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerY = height / 2;
    const channelData = this.transcribeFileState.channelData;

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const samples = Math.min(width, channelData.length);
    const step = width / samples;
    const blockSize = Math.floor(channelData.length / samples);

    for (let i = 0; i < samples; i++) {
      let sum = 0;
      for (let j = 0; j < blockSize; j++) {
        sum += Math.abs(channelData[i * blockSize + j]);
      }
      const average = sum / blockSize;
      const x = i * step;
      const amplitude = average * height * 0.8;
      const y = centerY + (i % 2 === 0 ? amplitude : -amplitude);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  private redrawFileWaveformWithProgress(): void {
    if (!this.fileWaveformCanvas || !this.transcribeFileState.channelData) return;

    this.drawFileWaveform();

    if (this.transcribeFileState.progress > 0) {
      const canvas = this.fileWaveformCanvas.nativeElement;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;
      const progressX = this.transcribeFileState.progress * width;
      ctx.strokeStyle = '#ff6b6b';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(progressX, 0);
      ctx.lineTo(progressX, height);
      ctx.stroke();
    }
  }

  toggleFilePlayback(): void {
    const audio = this.fileAudioPlayer?.nativeElement;
    if (!audio || !this.transcribeFileState.audioUrl) return;
    if (audio.paused) {
      audio.currentTime = 0;
      audio.play();
    } else {
      audio.pause();
    }
  }

  async transcribeFileAudio(): Promise<void> {
    if (!this.transcribeFileState.audioBlob || this.isTranscribingFile) return;

    try {
      this.isTranscribingFile = true;
      const audioFile = new File([this.transcribeFileState.audioBlob], 'transcribe.wav', { type: 'audio/wav' });
      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('language', this.fileInputLanguage);

      this.apiService.transcribeFile(formData).subscribe({
        next: (response) => {
          if (response.status === 'processing') {
            this.startFilePolling();
          } else {
            this.isTranscribingFile = false;
            alert(response.message || 'Failed to start transcription.');
          }
        },
        error: (error) => {
          console.error('Transcribe file request failed:', error);
          alert('Failed to start transcription. Please try again.');
          this.isTranscribingFile = false;
        }
      });
    } catch (error) {
      console.error('Error starting file transcription:', error);
      this.isTranscribingFile = false;
    }
  }

  private startFilePolling(): void {
    this.filePollingInterval = setInterval(() => {
      this.apiService.checkRunning().subscribe({
        next: (response) => {
          if (!response.running_whisper) {
            this.isTranscribingFile = false;
            this.stopFilePolling();
            this.refreshFileDownloads();
            this.cdr.detectChanges();
          }
        },
        error: (error) => {
          console.error('File polling error:', error);
          this.isTranscribingFile = false;
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

  formatMarkdown(text: string): SafeHtml {
    if (!text) return '';
    const html = text
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
    return this.sanitizer.sanitize(1, html) || '';
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
    this.stopRecordingLoop();
    this.stopPlaybackLoop();
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
