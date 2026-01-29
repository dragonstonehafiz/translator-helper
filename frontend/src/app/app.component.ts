import { Component, OnInit } from '@angular/core';
import { RouterOutlet, Router } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';
import { ApiService } from './services/api.service';
import { StateService } from './services/state.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent],
  template: `
    <app-navbar></app-navbar>
    <router-outlet></router-outlet>
  `,
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'Translator Helper';

  constructor(
    private apiService: ApiService,
    private stateService: StateService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.checkBackendReady();
  }

  private checkBackendReady(): void {
    this.apiService.getServerVariables().subscribe({
      next: (response) => {
        this.stateService.setLlmReady(response.llm_ready);
        this.stateService.setAudioReady(response.audio_ready);
        this.stateService.setReady(response.llm_ready && response.audio_ready);
        if (!(response.llm_ready && response.audio_ready)) {
          this.router.navigate(['/settings']);
        }
      },
      error: (error) => {
        console.error('Failed to check backend readiness:', error);
        this.stateService.setReady(false);
        this.router.navigate(['/settings']);
      }
    });
  }
}
