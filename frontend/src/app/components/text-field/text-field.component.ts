import { Component, Input, Output, EventEmitter, forwardRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';
import { TooltipIconComponent } from '../tooltip-icon/tooltip-icon.component';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
  selector: 'app-text-field',
  standalone: true,
  imports: [CommonModule, FormsModule, TooltipIconComponent],
  templateUrl: './text-field.component.html',
  styleUrl: './text-field.component.scss',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => TextFieldComponent),
      multi: true
    }
  ]
})
export class TextFieldComponent implements ControlValueAccessor {
  @Input() label = '';
  @Input() tooltip = '';
  @Input() placeholder = '';
  @Input() rows = 8;
  
  private _value = '';
  readMode = true;
  fontSize = 14;
  collapsed = false;
  
  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  constructor(private sanitizer: DomSanitizer) {}

  get value(): string {
    return this._value;
  }

  set value(val: string) {
    this._value = val;
    this.onChange(val);
    this.onTouched();
  }

  writeValue(value: string): void {
    this._value = value || '';
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  toggleMode(): void {
    this.readMode = !this.readMode;
  }

  toggleCollapsed(): void {
    this.collapsed = !this.collapsed;
  }

  adjustFontSize(delta: number): void {
    this.fontSize = Math.max(12, Math.min(24, this.fontSize + delta));
  }

  async copyToClipboard(): Promise<void> {
    if (!this.value) return;
    
    try {
      await navigator.clipboard.writeText(this.value);
    } catch (err) {
      console.error('Failed to copy text:', err);
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
}
