import { Component, Input, ViewChild, ElementRef, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-waveform-player',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './waveform-player.component.html',
  styleUrl: './waveform-player.component.scss'
})
export class WaveformPlayerComponent implements AfterViewInit, OnDestroy {
  @Input() selectionEnabled = false;

  @ViewChild('waveformCanvas') waveformCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('audioPlayer') audioPlayer?: ElementRef<HTMLAudioElement>;

  // Public state (template-bound)
  playbackTime = 0;
  playbackDuration = 0;
  isPlaying = false;

  // Private internal state
  private _audioBlob: Blob | null = null;
  private channelData: Float32Array | null = null;
  private decodedBuffer: AudioBuffer | null = null;
  private progress = 0;
  private selectionStart = 0;
  private selectionEnd = 0;
  private playbackRafId: number | null = null;
  private isSelecting = false;
  private selectionDragMode: 'new' | 'start' | 'end' = 'new';
  private ignoreNextClick = false;

  @Input() set audioBlob(blob: Blob | null) {
    this._audioBlob = blob;
    if (blob) {
      this.drawFromBlob(blob);
    } else {
      this.clearAudio();
    }
  }

  get hasAudio(): boolean {
    return this._audioBlob !== null;
  }

  get duration(): number {
    return this.playbackDuration;
  }

  ngAfterViewInit(): void {
    if (this.waveformCanvas) {
      this.drawWaveform();
      this.setupAudioListeners();
    }
  }

  ngOnDestroy(): void {
    this.stopPlaybackLoop();
    if (this.audioPlayer && this.audioPlayer.nativeElement.src) {
      URL.revokeObjectURL(this.audioPlayer.nativeElement.src);
    }
  }

  private setupAudioListeners(): void {
    if (!this.audioPlayer) return;
    const audio = this.audioPlayer.nativeElement;

    audio.addEventListener('timeupdate', () => {
      if (audio.duration) {
        this.progress = audio.currentTime / audio.duration;
        this.redrawWithProgress();
      }
      this.playbackTime = audio.currentTime || 0;
      if (this.selectionEnabled && this.hasSelection() && audio.currentTime >= this.selectionEnd) {
        audio.pause();
        audio.currentTime = this.selectionEnd;
      }
    });

    audio.addEventListener('loadedmetadata', () => {
      this.playbackDuration = Number.isFinite(audio.duration) ? audio.duration : 0;
      if (this.playbackDuration > 0) {
        this.selectionStart = 0;
        this.selectionEnd = this.playbackDuration;
        this.redrawWithProgress();
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

  private drawWaveform(): void {
    if (!this.waveformCanvas) return;
    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = canvas.offsetHeight * dpr;
    ctx.scale(dpr, dpr);

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerY = height / 2;

    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();
  }

  private async drawFromBlob(blob: Blob): Promise<void> {
    if (!this.waveformCanvas) return;
    const canvas = this.waveformCanvas.nativeElement;

    try {
      const arrayBuffer = await blob.arrayBuffer();
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.decodedBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const channel = this.decodedBuffer.getChannelData(0);

      // Downsample to fit canvas width
      const samples = Math.min(canvas.offsetWidth, channel.length);
      const blockSize = Math.ceil(channel.length / samples);
      this.channelData = new Float32Array(samples);

      for (let i = 0; i < samples; i++) {
        let sum = 0;
        for (let j = 0; j < blockSize; j++) {
          sum += Math.abs(channel[i * blockSize + j] || 0);
        }
        this.channelData[i] = sum / blockSize;
      }

      // Set audio source
      const url = URL.createObjectURL(blob);
      if (this.audioPlayer) {
        this.audioPlayer.nativeElement.src = url;
      }

      // Draw initial waveform
      this.drawWaveformContent();
      if (this.selectionEnabled) {
        this.drawSelectionOverlay();
      }
    } catch (err) {
      console.error('Failed to decode audio:', err);
    }
  }

  private drawWaveformContent(): void {
    if (!this.waveformCanvas || !this.channelData) return;
    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = canvas.offsetHeight * dpr;
    ctx.scale(dpr, dpr);

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    const centerY = height / 2;

    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 1;
    ctx.beginPath();

    for (let i = 0; i < this.channelData.length; i++) {
      const x = (i / this.channelData.length) * width;
      const amplitude = this.channelData[i] * centerY * 0.8;
      const y = centerY + (i % 2 === 0 ? amplitude : -amplitude);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  }

  private redrawWithProgress(): void {
    if (!this.waveformCanvas) return;
    this.drawWaveformContent();
    if (this.selectionEnabled) {
      this.drawSelectionOverlay();
    }

    // Draw progress line
    if (this.progress > 0) {
      const canvas = this.waveformCanvas.nativeElement;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const width = canvas.offsetWidth;
      const dpr = window.devicePixelRatio || 1;
      const progressX = (this.progress * width);

      ctx.strokeStyle = '#ff6b6b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(progressX, 0);
      ctx.lineTo(progressX, canvas.offsetHeight);
      ctx.stroke();
    }
  }

  private drawSelectionOverlay(): void {
    if (!this.waveformCanvas || !this.selectionEnabled) return;
    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;

    const startX = (this.selectionStart / this.playbackDuration) * width;
    const endX = (this.selectionEnd / this.playbackDuration) * width;

    // Highlight unselected regions
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillRect(0, 0, startX, height);
    ctx.fillRect(endX, 0, width - endX, height);

    // Draw selection handles
    ctx.strokeStyle = '#18a0fb';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(startX, 0);
    ctx.lineTo(startX, height);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(endX, 0);
    ctx.lineTo(endX, height);
    ctx.stroke();
  }

  private startPlaybackLoop(): void {
    const tick = () => {
      if (this.isPlaying && this.audioPlayer) {
        const audio = this.audioPlayer.nativeElement;
        if (audio.duration) {
          this.progress = audio.currentTime / audio.duration;
          this.playbackTime = audio.currentTime;
        }
        this.redrawWithProgress();
        this.playbackRafId = requestAnimationFrame(tick);
      }
    };
    this.playbackRafId = requestAnimationFrame(tick);
  }

  private stopPlaybackLoop(): void {
    if (this.playbackRafId !== null) {
      cancelAnimationFrame(this.playbackRafId);
      this.playbackRafId = null;
    }
  }

  togglePlayback(): void {
    if (!this.audioPlayer) return;
    const audio = this.audioPlayer.nativeElement;

    if (this.isPlaying) {
      audio.pause();
    } else {
      if (this.selectionEnabled && this.hasSelection()) {
        audio.currentTime = this.selectionStart;
      } else {
        audio.currentTime = 0;
      }
      audio.play().catch(err => console.error('Playback failed:', err));
    }
  }

  handleMouseDown(event: MouseEvent): void {
    if (!this.selectionEnabled || !this.waveformCanvas) return;
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const time = (x / canvas.offsetWidth) * this.playbackDuration;

    const startX = (this.selectionStart / this.playbackDuration) * canvas.offsetWidth;
    const endX = (this.selectionEnd / this.playbackDuration) * canvas.offsetWidth;

    if (Math.abs(x - startX) < 8) {
      this.selectionDragMode = 'start';
    } else if (Math.abs(x - endX) < 8) {
      this.selectionDragMode = 'end';
    } else {
      this.selectionDragMode = 'new';
      this.selectionStart = time;
      this.selectionEnd = time;
    }

    this.isSelecting = true;
    this.ignoreNextClick = true;
    this.updateSelection(time);
  }

  handleMouseMove(event: MouseEvent): void {
    if (!this.isSelecting || !this.waveformCanvas) return;
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const time = (x / canvas.offsetWidth) * this.playbackDuration;

    this.updateSelection(time);
  }

  handleMouseUp(event?: MouseEvent): void {
    if (!this.isSelecting) return;
    this.isSelecting = false;

    if (this.selectionStart > this.selectionEnd) {
      [this.selectionStart, this.selectionEnd] = [this.selectionEnd, this.selectionStart];
    }

    this.redrawWithProgress();
  }

  handleClick(event: MouseEvent): void {
    if (!this.waveformCanvas || this.ignoreNextClick) {
      this.ignoreNextClick = false;
      return;
    }

    if (!this.audioPlayer) return;
    const canvas = this.waveformCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const time = (x / canvas.offsetWidth) * this.playbackDuration;

    let seekTime = time;
    if (this.selectionEnabled && this.hasSelection()) {
      seekTime = Math.max(this.selectionStart, Math.min(this.selectionEnd, time));
    }

    this.audioPlayer.nativeElement.currentTime = seekTime;
  }

  private updateSelection(time: number): void {
    time = Math.max(0, Math.min(this.playbackDuration, time));

    switch (this.selectionDragMode) {
      case 'start':
        this.selectionStart = time;
        break;
      case 'end':
        this.selectionEnd = time;
        break;
      case 'new':
        this.selectionEnd = time;
        break;
    }

    if (this.selectionStart > this.selectionEnd) {
      [this.selectionStart, this.selectionEnd] = [this.selectionEnd, this.selectionStart];
    }

    this.redrawWithProgress();
  }

  private hasSelection(): boolean {
    return this.selectionStart < this.selectionEnd;
  }

  private isFullSelection(): boolean {
    return this.selectionStart === 0 && this.selectionEnd === this.playbackDuration;
  }

  async getActiveBlob(): Promise<Blob | null> {
    if (!this._audioBlob || !this.selectionEnabled || !this.hasSelection() || this.isFullSelection()) {
      return this._audioBlob;
    }

    // Return clipped audio blob
    if (!this.decodedBuffer) return this._audioBlob;

    const startSample = Math.floor(this.selectionStart * this.decodedBuffer.sampleRate);
    const endSample = Math.floor(this.selectionEnd * this.decodedBuffer.sampleRate);
    const clippedLength = endSample - startSample;

    const audioContext = new AudioContext();
    const clippedBuffer = audioContext.createBuffer(
      this.decodedBuffer.numberOfChannels,
      clippedLength,
      this.decodedBuffer.sampleRate
    );

    // Copy channel data
    for (let i = 0; i < this.decodedBuffer.numberOfChannels; i++) {
      const sourceChannel = this.decodedBuffer.getChannelData(i);
      const targetChannel = clippedBuffer.getChannelData(i);
      targetChannel.set(sourceChannel.slice(startSample, endSample));
    }

    await audioContext.close();
    return this.encodeWav(clippedBuffer);
  }

  private encodeWav(audioBuffer: AudioBuffer): Blob {
    const channels = [];
    for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
      channels.push(audioBuffer.getChannelData(i));
    }

    const sampleRate = audioBuffer.sampleRate;
    const format = 1; // PCM
    const numberOfChannels = audioBuffer.numberOfChannels;
    const length = audioBuffer.length;

    const arrayBuffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
    const view = new DataView(arrayBuffer);

    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * numberOfChannels * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, format, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * numberOfChannels * 2, true);

    const offset = 44;
    const volume = 0.8;
    let index = 0;
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const sample = Math.max(-1, Math.min(1, channels[channel][i])) * volume;
        view.setInt16(offset + index, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
        index += 2;
      }
    }

    return new Blob([arrayBuffer], { type: 'audio/wav' });
  }

  getDecodedBuffer(): AudioBuffer | null {
    return this.decodedBuffer;
  }

  clearAudio(): void {
    this.channelData = null;
    this.decodedBuffer = null;
    this.playbackTime = 0;
    this.playbackDuration = 0;
    this.progress = 0;
    this.isPlaying = false;
    this.selectionStart = 0;
    this.selectionEnd = 0;

    if (this.audioPlayer) {
      this.audioPlayer.nativeElement.src = '';
    }

    this.drawWaveform();
  }

  formatDuration(seconds: number): string {
    const totalSeconds = Math.max(0, seconds || 0);
    const mins = Math.floor(totalSeconds / 60);
    const secs = Math.floor(totalSeconds % 60);
    const ms = Math.floor((totalSeconds - Math.floor(totalSeconds)) * 1000);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
}
