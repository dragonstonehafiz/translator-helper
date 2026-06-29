import { Component, OnInit, OnDestroy } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { StateService } from '../../services/state.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss'
})
export class NavbarComponent implements OnInit, OnDestroy {
  llmReady = false;
  audioReady = false;
  private readinessSubscription?: Subscription;

  constructor(private stateService: StateService) {}

  ngOnInit(): void {
    this.readinessSubscription = new Subscription();
    this.readinessSubscription.add(
      this.stateService.llmReady$.subscribe(ready => {
        this.llmReady = ready === true;
      })
    );
    this.readinessSubscription.add(
      this.stateService.audioReady$.subscribe(ready => {
        this.audioReady = ready === true;
      })
    );
  }

  ngOnDestroy(): void {
    this.readinessSubscription?.unsubscribe();
  }
}
