import { Component, ViewChild, ElementRef, AfterViewInit, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SubsectionComponent } from '../../components/subsection/subsection.component';
import { TooltipIconComponent } from '../../components/tooltip-icon/tooltip-icon.component';
import { FileUploadComponent } from '../../components/file-upload/file-upload.component';
import { TextFieldComponent } from '../../components/text-field/text-field.component';
import { ApiService } from '../../services/api.service';
import { StateService } from '../../services/state.service';

@Component({
  selector: 'app-transcribe',
  standalone: true,
  imports: [CommonModule, FormsModule, SubsectionComponent, FileUploadComponent, TextFieldComponent, TooltipIconComponent],
  templateUrl: './transcribe.component.html',
  styleUrl: './transcribe.component.scss'
})
export class TranscribeComponent implements AfterViewInit, OnDestroy {
  @ViewChild('waveformCanvas') waveformCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('audioPlayer') audioPlayer?: ElementRef<HTMLAudioElement>;
  
  translateLineCollapsed = true;
  isRecording = false;
  recordingDuration = 0;
  recordedAudioUrl: string | null = null;
  recordedAudioBlob: Blob | null = null;
  private recordingInterval?: any;
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
      });
    }
    
    // Set up canvas click for seeking
    if (this.waveformCanvas) {
      this.waveformCanvas.nativeElement.addEventListener('click', (event) => {
        this.handleWaveformClick(event);
      });
      
      // Add cursor pointer style
      this.waveformCanvas.nativeElement.style.cursor = 'pointer';
    }
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
      
      // Draw silent waveform when starting new recording
      this.drawWaveform(true);
      
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
        
        // Trigger change detection
        this.cdr.detectChanges();
      };
      
      // Start recording
      this.mediaRecorder.start();
      this.isRecording = true;
      this.recordingDuration = 0;
      
      // Start timer
      this.recordingInterval = setInterval(() => {
        this.recordingDuration++;
      }, 1000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please ensure you have granted microphone permissions.');
    }
  }

  stopRecording(): void {
    this.isRecording = false;
    
    // Stop timer
    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
      this.recordingInterval = undefined;
    }
    
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
      
      // Get audio data from first channel
      const channelData = audioBuffer.getChannelData(0);
      this.audioChannelData = channelData;
      
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
    if (!this.waveformCanvas || !this.audioPlayer || !this.recordedAudioUrl) return;
    
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;
    
    // Calculate seek position
    const seekPercent = x / width;
    const audio = this.audioPlayer.nativeElement;
    
    if (audio.duration) {
      audio.currentTime = seekPercent * audio.duration;
    }
  }

  async transcribeAudio(): Promise<void> {
    if (!this.recordedAudioBlob || this.isTranscribing) return;

    try {
      this.isTranscribing = true;

      // Convert blob to File
      const extension = this.recordedAudioBlob.type.includes('webm') ? 'webm' : 'mp4';
      const audioFile = new File([this.recordedAudioBlob], `recording.${extension}`, { type: this.recordedAudioBlob.type });

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

  formatMarkdown(text: string): SafeHtml {
    if (!text) return '';
    const html = text
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
    return this.sanitizer.sanitize(1, html) || '';
  }

  formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  ngOnDestroy(): void {
    this.stopPolling();
    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
    }
  }
}
