import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  constructor(private router: Router) {}

  navigateToLibrary(): void {
    this.router.navigate(['/library']);
  }

  navigateToTranscribe(): void {
    this.router.navigate(['/transcribe']);
  }

  navigateToTranslate(): void {
    this.router.navigate(['/translate']);
  }
}
