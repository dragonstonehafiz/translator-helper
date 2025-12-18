import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { Subscription } from 'rxjs';

interface SidebarSection {
  id: string;
  title: string;
  isActive: boolean;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent implements OnInit, OnDestroy {
  sections: SidebarSection[] = [];
  private routerSubscription?: Subscription;

  constructor(private router: Router) {}

  ngOnInit(): void {
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
  }

  @HostListener('window:scroll', [])
  onScroll(): void {
    this.updateActiveSections();
  }

  private detectSections(): void {
    // First try to find app-subsection elements
    const appSubsections = document.querySelectorAll('app-subsection');
    
    if (appSubsections.length > 0) {
      // For app-subsection components, read the title attribute directly
      this.sections = Array.from(appSubsections).map((appElement, index) => {
        // Get title from the title attribute
        const title = appElement.getAttribute('title') || `Section ${index + 1}`;
        
        // Use the inner .subsection div for scrolling
        const subsectionDiv = appElement.querySelector('.subsection');
        let id = subsectionDiv?.id || '';
        if (!id && subsectionDiv) {
          id = `section-${index}`;
          subsectionDiv.id = id;
        }
        
        return {
          id,
          title,
          isActive: false
        };
      });
    } else {
      // Fallback for old-style div.subsection elements
      const subsections = document.querySelectorAll('.subsection');
      this.sections = Array.from(subsections).map((element, index) => {
        const titleElement = element.querySelector('.subsection-title');
        const title = titleElement?.textContent?.trim() || `Section ${index + 1}`;
        
        let id = element.id;
        if (!id) {
          id = `section-${index}`;
          element.id = id;
        }
        
        return {
          id,
          title,
          isActive: false
        };
      });
    }

    this.updateActiveSections();
  }

  private updateActiveSections(): void {
    if (this.sections.length === 0) return;

    const scrollPosition = window.scrollY + 100; // Offset for better UX

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
      const offset = 20;
      const elementPosition = element.getBoundingClientRect().top + window.scrollY;
      const offsetPosition = elementPosition - navbarHeight - offset;
      
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  }
}
