import { Component, ViewChild, ElementRef, AfterViewInit, ChangeDetectorRef, OnDestroy, HostListener } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { LoadingTextIndicatorComponent } from '../../components/loading-text-indicator/loading-text-indicator.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';

@Component({
  selector: 'app-transcribe',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, FileUploadComponent, TextFieldComponent, TooltipIconComponent, LoadingTextIndicatorComponent],
  templateUrl: './transcribe.component.html',
  styleUrl: './transcribe.component.scss'
})
export class TranscribeComponent implements AfterViewInit, OnDestroy {
  @ViewChild('waveformCanvas') waveformCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('audioPlayer') audioPlayer?: ElementRef<HTMLAudioElement>;
  
  translateLineCollapsed = true;
  isRecording = false;
  recordingDuration = 0;
  recordedDuration = 0;
  playbackTime = 0;
  playbackDuration = 0;
  isPlaying = false;
  selectionStart = 0;
  selectionEnd = 0;
  private isSelecting = false;
  private selectionDragMode: 'new' | 'start' | 'end' = 'new';
  private ignoreNextClick = false;
  private decodedAudioBuffer: AudioBuffer | null = null;
  private playbackRafId: number | null = null;
  recordedAudioUrl: string | null = null;
  recordedAudioBlob: Blob | null = null;
  private recordingRafId: number | null = null;
  private recordingStartTime = 0;
  private mediaRecorder?: MediaRecorder;
  private audioChunks: Blob[] = [];
  private audioChannelData: Float32Array | null = null;
  private audioProgress = 0;
  
  // Transcript state
  transcript = '';
  transcriptReadMode = true;
  transcriptFontSize = 16;
  isTranscribing = false;
  private pollingInterval?: any;
  
  // Language settings
  inputLanguage = 'ja';
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
  
  constructor(
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer,
    private apiService: ApiService,
    private stateService: StateService
  ) {}

  ngAfterViewInit(): void {
    // Draw initial silent waveform
    setTimeout(() => this.drawWaveform(true), 100);
    
    // Set up audio player event listeners
    if (this.audioPlayer) {
      const audio = this.audioPlayer.nativeElement;
      audio.addEventListener('timeupdate', () => {
        if (audio.duration) {
          this.audioProgress = audio.currentTime / audio.duration;
          this.redrawWaveformWithProgress();
        }
        this.playbackTime = audio.currentTime || 0;
        if (this.hasSelection() && audio.currentTime >= this.selectionEnd) {
          audio.pause();
          audio.currentTime = this.selectionEnd;
        }
      });
      audio.addEventListener('loadedmetadata', () => {
        this.playbackDuration = Number.isFinite(audio.duration) ? audio.duration : 0;
        this.recordedDuration = this.playbackDuration || this.recordedDuration;
        if (this.playbackDuration > 0) {
          this.selectionStart = 0;
          this.selectionEnd = this.playbackDuration;
          this.redrawWaveformWithProgress();
        }
      });
      audio.addEventListener('play', () => {
        this.isPlaying = true;
        this.startPlaybackLoop();
      });
      audio.addEventListener('pause', () => {
        this.isPlaying = false;
        this.stopPlaybackLoop();
      });
      audio.addEventListener('ended', () => {
        this.isPlaying = false;
        this.stopPlaybackLoop();
      });
    }
    
    // Set up canvas click for seeking
    if (this.waveformCanvas) {
      const canvas = this.waveformCanvas.nativeElement;
      canvas.addEventListener('click', (event) => this.handleWaveformClick(event));
      canvas.addEventListener('mousedown', (event) => this.handleWaveformMouseDown(event));
      canvas.addEventListener('mousemove', (event) => this.handleWaveformMouseMove(event));
      canvas.addEventListener('mouseup', () => this.handleWaveformMouseUp());
      canvas.addEventListener('mouseleave', () => this.handleWaveformMouseUp());
      
      // Add cursor pointer style
      this.waveformCanvas.nativeElement.style.cursor = 'pointer';
    }
  }

  @HostListener('window:keydown', ['$event'])
  handleWindowKeydown(event: KeyboardEvent): void {
    if (!this.isSpacebar(event)) return;
    if (this.isEditableTarget(event.target)) return;
    if (!this.recordedAudioUrl) return;
    event.preventDefault();
    this.togglePlayback();
  }

  async startRecording(): Promise<void> {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false
        }
      });
      
      // Clear previous recording
      if (this.recordedAudioUrl) {
        URL.revokeObjectURL(this.recordedAudioUrl);
        this.recordedAudioUrl = null;
        this.recordedAudioBlob = null;
      }
      this.decodedAudioBuffer = null;
      
      // Draw silent waveform when starting new recording
      this.drawWaveform(true);
      this.recordedDuration = 0;
      this.selectionStart = 0;
      this.selectionEnd = 0;
      
      // Reset audio chunks
      this.audioChunks = [];
      
      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(stream);
      
      // Collect audio data
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };
      
      // Handle recording stop
      this.mediaRecorder.onstop = async () => {
        // Create blob from chunks with proper MIME type
        const mimeType = this.mediaRecorder?.mimeType || 'audio/webm';
        const audioBlob = new Blob(this.audioChunks, { type: mimeType });
        this.recordedAudioBlob = audioBlob;
        this.recordedAudioUrl = URL.createObjectURL(audioBlob);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
        
        // Analyze and draw waveform from actual audio
        await this.drawWaveformFromAudio(audioBlob);
        if (this.audioPlayer?.nativeElement) {
          this.audioPlayer.nativeElement.currentTime = 0;
        }
        
        // Trigger change detection
        this.cdr.detectChanges();
      };
      
      // Start recording
      this.mediaRecorder.start();
      this.isRecording = true;
      this.recordingDuration = 0;
      this.playbackTime = 0;
      this.playbackDuration = 0;
      this.recordingStartTime = performance.now();
      this.startRecordingLoop();
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please ensure you have granted microphone permissions.');
    }
  }

  stopRecording(): void {
    this.isRecording = false;
    this.recordedDuration = this.recordingDuration;
    this.playbackDuration = this.recordedDuration;
    this.selectionStart = 0;
    this.selectionEnd = this.playbackDuration;
    this.stopRecordingLoop();
    
    // Stop timer
    // Stop MediaRecorder
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
  }

  private drawWaveform(silent: boolean = false): void {
    if (!this.waveformCanvas) return;
    
    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas resolution
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerY = height / 2;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    // Draw flat line for silent/no recording
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

      // Read audio data
      const arrayBuffer = await audioBlob.arrayBuffer();
      const audioContext = new AudioContext();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      this.decodedAudioBuffer = audioBuffer;
      
      // Get audio data from first channel
      const channelData = audioBuffer.getChannelData(0);
      this.audioChannelData = channelData;
      this.playbackDuration = audioBuffer.duration;
      this.recordedDuration = audioBuffer.duration;
      this.selectionStart = 0;
      this.selectionEnd = audioBuffer.duration;
      
      // Set canvas resolution
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;
      const centerY = height / 2;

      // Clear canvas
      ctx.clearRect(0, 0, width, height);
      ctx.strokeStyle = '#667eea';
      ctx.lineWidth = 2;
      ctx.beginPath();

      // Calculate samples to display
      const samples = Math.min(width, channelData.length);
      const step = width / samples;
      const blockSize = Math.floor(channelData.length / samples);

      for (let i = 0; i < samples; i++) {
        // Get average amplitude for this block
        let sum = 0;
        for (let j = 0; j < blockSize; j++) {
          sum += Math.abs(channelData[i * blockSize + j]);
        }
        const average = sum / blockSize;
        
        const x = i * step;
        const amplitude = average * height * 0.8; // Scale amplitude
        const y = centerY + (i % 2 === 0 ? amplitude : -amplitude);
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();
      this.drawSelectionOverlay(ctx, width, height);
      
      // Close audio context
      await audioContext.close();
    } catch (error) {
      console.error('Error drawing waveform:', error);
      // Fall back to silent waveform on error
      this.drawWaveform(true);
    }
  }

  private redrawWaveformWithProgress(): void {
    if (!this.waveformCanvas || !this.audioChannelData) return;
    
    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerY = height / 2;

    // Clear and redraw waveform
    ctx.clearRect(0, 0, width, height);
    
    // Draw waveform
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const samples = Math.min(width, this.audioChannelData.length);
    const step = width / samples;
    const blockSize = Math.floor(this.audioChannelData.length / samples);

    for (let i = 0; i < samples; i++) {
      let sum = 0;
      for (let j = 0; j < blockSize; j++) {
        sum += Math.abs(this.audioChannelData[i * blockSize + j]);
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
    
    // Draw progress line
    if (this.audioProgress > 0) {
      const progressX = this.audioProgress * width;
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
    if (!this.waveformCanvas || !this.audioPlayer || !this.recordedAudioUrl) return;
    
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;
    
    // Calculate seek position
    const seekPercent = x / width;
    const audio = this.audioPlayer.nativeElement;
    
    if (audio.duration) {
      let targetTime = seekPercent * audio.duration;
      if (this.hasSelection()) {
        targetTime = Math.min(Math.max(targetTime, this.selectionStart), this.selectionEnd);
      }
      audio.currentTime = targetTime;
    }
  }

  private handleWaveformMouseDown(event: MouseEvent): void {
    if (!this.waveformCanvas || !this.playbackDuration || !this.recordedAudioUrl) return;
    this.ignoreNextClick = true;
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;
    const time = (x / width) * this.playbackDuration;

    const startX = (this.selectionStart / this.playbackDuration) * width;
    const endX = (this.selectionEnd / this.playbackDuration) * width;
    const handleThreshold = 8;

    if (Math.abs(x - startX) <= handleThreshold) {
      this.selectionDragMode = 'start';
    } else if (Math.abs(x - endX) <= handleThreshold) {
      this.selectionDragMode = 'end';
    } else {
      this.selectionDragMode = 'new';
      this.selectionStart = time;
      this.selectionEnd = time;
    }

    this.isSelecting = true;
    this.updateSelection(time);
  }

  private handleWaveformMouseMove(event: MouseEvent): void {
    if (!this.isSelecting || !this.waveformCanvas || !this.playbackDuration) return;
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;
    const time = (x / width) * this.playbackDuration;
    this.updateSelection(time);
  }

  private handleWaveformMouseUp(): void {
    if (!this.isSelecting) return;
    this.isSelecting = false;
    if (this.selectionEnd < this.selectionStart) {
      const temp = this.selectionStart;
      this.selectionStart = this.selectionEnd;
      this.selectionEnd = temp;
    }
    this.redrawWaveformWithProgress();
  }

  private updateSelection(time: number): void {
    const clamped = Math.max(0, Math.min(time, this.playbackDuration));
    if (this.selectionDragMode === 'start') {
      this.selectionStart = clamped;
    } else if (this.selectionDragMode === 'end') {
      this.selectionEnd = clamped;
    } else {
      this.selectionEnd = clamped;
    }
    if (this.selectionEnd < this.selectionStart) {
      const temp = this.selectionStart;
      this.selectionStart = this.selectionEnd;
      this.selectionEnd = temp;
    }
    this.redrawWaveformWithProgress();
  }

  private hasSelection(): boolean {
    return this.playbackDuration > 0 && this.selectionEnd > this.selectionStart;
  }

  private drawSelectionOverlay(ctx: CanvasRenderingContext2D, width: number, height: number): void {
    if (!this.hasSelection()) return;
    const startX = (this.selectionStart / this.playbackDuration) * width;
    const endX = (this.selectionEnd / this.playbackDuration) * width;

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
    if (!this.audioPlayer || !this.recordedAudioUrl) return;
    const audio = this.audioPlayer.nativeElement;
    audio.play();
  }

  togglePlayback(): void {
    if (!this.audioPlayer || !this.recordedAudioUrl) return;
    const audio = this.audioPlayer.nativeElement;
    if (audio.paused) {
      if (this.hasSelection()) {
        audio.currentTime = this.selectionStart;
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
          const end = this.selectionEnd;
          if (audio.currentTime >= end - 0.005) {
            audio.currentTime = end;
            audio.pause();
            this.playbackTime = end;
            this.audioProgress = end / audio.duration;
            this.redrawWaveformWithProgress();
            this.stopPlaybackLoop();
            return;
          }
        }
        this.audioProgress = audio.currentTime / audio.duration;
        this.playbackTime = audio.currentTime || 0;
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
      if (!this.isRecording) {
        this.stopRecordingLoop();
        return;
      }
      this.recordingDuration = (performance.now() - this.recordingStartTime) / 1000;
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
    if (!this.recordedAudioBlob || this.isTranscribing) return;

    try {
      this.isTranscribing = true;

      const clippedBlob = await this.getClippedAudioBlob();
      const mimeType = clippedBlob.type || this.recordedAudioBlob.type;
      const extension = mimeType.includes('wav')
        ? 'wav'
        : (mimeType.includes('webm') ? 'webm' : 'mp4');
      const audioFile = new File([clippedBlob], `recording.${extension}`, { type: mimeType });

      // Start transcription
      this.apiService.transcribeAudio(audioFile, this.inputLanguage).subscribe({
        next: (response) => {
          if (response.status === 'processing') {
            // Start polling for result
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

  private startPolling(): void {
    this.pollingInterval = setInterval(() => {
      this.apiService.getTranscriptionResult().subscribe({
        next: (response) => {
          if (response.status === 'complete' && response.result) {
            // Transcription complete
            this.transcript = response.result.data;
            this.isTranscribing = false;
            this.stopPolling();
            this.cdr.detectChanges();
          } else if (response.status === 'error') {
            // Error occurred
            console.error('Transcription error:', response.message);
            alert('Transcription failed: ' + (response.message || 'Unknown error'));
            this.isTranscribing = false;
            this.stopPolling();
          } else if (response.status === 'idle') {
            // No transcription in progress
            this.isTranscribing = false;
            this.stopPolling();
          }
          // If status is 'processing', continue polling
        },
        error: (error) => {
          console.error('Polling error:', error);
          this.isTranscribing = false;
          this.stopPolling();
        }
      });
    }, 1000); // Poll every second
  }

  private stopPolling(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = undefined;
    }
  }

  toggleTranscriptMode(): void {
    this.transcriptReadMode = !this.transcriptReadMode;
  }

  adjustTranscriptFontSize(delta: number): void {
    this.transcriptFontSize = Math.max(12, Math.min(24, this.transcriptFontSize + delta));
  }

  getDisplayCurrentTime(): number {
    if (this.isRecording) {
      return 0;
    }
    if (this.playbackDuration > 0 && this.selectionEnd > this.selectionStart) {
      return Math.max(0, this.playbackTime - this.selectionStart);
    }
    return this.playbackTime;
  }

  getDisplayTotalTime(): number {
    if (this.isRecording) {
      return this.recordingDuration;
    }
    if (this.playbackDuration > 0 && this.selectionEnd > this.selectionStart) {
      return Math.max(0, this.selectionEnd - this.selectionStart);
    }
    return this.playbackDuration || this.recordedDuration;
  }

  private async getClippedAudioBlob(): Promise<Blob> {
    if (!this.recordedAudioBlob) {
      throw new Error('No recording available');
    }

    const duration = this.playbackDuration || this.recordedDuration;
    if (!this.hasSelection() || this.isFullSelection(duration)) {
      return this.recordedAudioBlob;
    }

    const audioBuffer = await this.getDecodedAudioBuffer();
    const sampleRate = audioBuffer.sampleRate;
    const startSample = Math.floor(this.selectionStart * sampleRate);
    const endSample = Math.floor(this.selectionEnd * sampleRate);
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
    if (this.decodedAudioBuffer) {
      return this.decodedAudioBuffer;
    }
    if (!this.recordedAudioBlob) {
      throw new Error('No recording available');
    }
    const arrayBuffer = await this.recordedAudioBlob.arrayBuffer();
    const audioContext = new AudioContext();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    await audioContext.close();
    this.decodedAudioBuffer = audioBuffer;
    return audioBuffer;
  }

  private isFullSelection(duration: number): boolean {
    if (!duration) return true;
    const epsilon = 0.01;
    return Math.abs(this.selectionStart) <= epsilon && Math.abs(this.selectionEnd - duration) <= epsilon;
  }

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
