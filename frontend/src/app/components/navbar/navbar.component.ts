import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { StateService } from '../../services/state.service';
import { filter } from 'rxjs/operators';
import { Subscription } from 'rxjs';

interface NavSection {
  id: string;
  title: string;
  isActive: boolean;
}

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
  sections: NavSection[] = [];
  private routerSubscription?: Subscription;
  private readinessSubscription?: Subscription;

  constructor(private stateService: StateService, private router: Router) {}

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

    this.detectSections();
    
    // Re-detect sections when route changes
    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        setTimeout(() => this.detectSections(), 100);
      });
  }

  ngOnDestroy(): void {
    this.routerSubscription?.unsubscribe();
    this.readinessSubscription?.unsubscribe();
  }

  @HostListener('window:scroll', [])
  onScroll(): void {
    this.updateActiveSections();
  }

  private detectSections(): void {
    const appSubsections = document.querySelectorAll('app-subsection');
    
    if (appSubsections.length > 0) {
      this.sections = Array.from(appSubsections).map((appElement, index) => {
        const title = appElement.getAttribute('title') || `Section ${index + 1}`;
        
        const subsectionDiv = appElement.querySelector('.subsection');
        let id = subsectionDiv?.id || '';
        if (!id && subsectionDiv) {
          id = `section-${index}`;
          (subsectionDiv as HTMLElement).id = id;
        }
        
        return {
          id,
          title,
          isActive: false
        };
      });
    } else {
      this.sections = [];
    }

    this.updateActiveSections();
  }

  private updateActiveSections(): void {
    if (this.sections.length === 0) return;

    const scrollPosition = window.scrollY + 120; // Offset for navbar height

    for (const section of this.sections) {
      const element = document.getElementById(section.id);
      if (element) {
        const rect = element.getBoundingClientRect();
        const elementTop = window.scrollY + rect.top;
        const elementBottom = elementTop + rect.height;
        
        section.isActive = scrollPosition >= elementTop && scrollPosition < elementBottom;
      }
    }
  }

  scrollToSection(sectionId: string): void {
    const element = document.getElementById(sectionId);
    if (element) {
      const navbarHeight = 60;
      const subnavHeight = 50;
      const offset = 20;
      const elementPosition = element.getBoundingClientRect().top + window.scrollY;
      const offsetPosition = elementPosition - navbarHeight - subnavHeight - offset;
      
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  }
}
