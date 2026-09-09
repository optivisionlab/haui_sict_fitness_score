import {
  Component,
  AfterViewInit,
  OnDestroy,
  ElementRef,
  inject,
  PLATFORM_ID
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-intro',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './intro.component.html',
  styleUrl: './intro.component.scss'
})
export class IntroComponent implements AfterViewInit, OnDestroy {
  private router = inject(Router);
  private elRef = inject(ElementRef);
  private platformId = inject(PLATFORM_ID);

  private revealObserver?: IntersectionObserver;
  private countObserver?: IntersectionObserver;
  private timeouts: any[] = [];

  ngAfterViewInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    const host = this.elRef.nativeElement;
    const scrollContainer = host.querySelector('.intro-page') || null;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Reveal elements animation
    const revealEls = host.querySelectorAll('.reveal');
    if (reduceMotion || !('IntersectionObserver' in window)) {
      revealEls.forEach((el: Element) => el.classList.add('in-view'));
    } else {
      this.revealObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add('in-view');
              this.revealObserver?.unobserve(entry.target);
            }
          });
        },
        { root: scrollContainer, threshold: 0.12, rootMargin: '0px 0px -30px 0px' }
      );
      revealEls.forEach((el: Element) => this.revealObserver?.observe(el));
    }

    // 2. Count-up animation
    const countEls = host.querySelectorAll('[data-count-to]');
    if (reduceMotion || !('IntersectionObserver' in window)) {
      countEls.forEach((el: Element) => {
        const target = el.getAttribute('data-count-to');
        if (target) el.textContent = target;
      });
    } else {
      this.countObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              this.animateCount(entry.target as HTMLElement);
              this.countObserver?.unobserve(entry.target);
            }
          });
        },
        { root: scrollContainer, threshold: 0.4 }
      );
      countEls.forEach((el: Element) => this.countObserver?.observe(el));
    }

    // 3. Hero score bars grow animation
    const bars = host.querySelectorAll('[data-grow]');
    bars.forEach((bar: Element, i: number) => {
      const target = bar.getAttribute('data-grow') + '%';
      const barEl = bar as HTMLElement;
      if (reduceMotion) {
        barEl.style.height = target;
        return;
      }
      const t = setTimeout(() => {
        barEl.style.height = target;
      }, 350 + i * 140);
      this.timeouts.push(t);
    });
  }

  private animateCount(el: HTMLElement): void {
    const rawTarget = el.getAttribute('data-count-to');
    if (!rawTarget) return;

    const target = parseFloat(rawTarget);
    const isDecimal = rawTarget.indexOf('.') !== -1;
    const duration = 1200;
    let start: number | null = null;

    const step = (timestamp: number) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const value = target * eased;
      el.textContent = isDecimal ? value.toFixed(2) : Math.round(value).toString();

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = isDecimal ? target.toFixed(2) : target.toString();
      }
    };
    requestAnimationFrame(step);
  }

  navigateToLogin(): void {
    this.router.navigate(['/login']);
  }

  scrollToSection(event: Event, sectionId: string): void {
    event.preventDefault();
    const host = this.elRef.nativeElement;
    const target = host.querySelector(`#${sectionId}`);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  scrollToTop(event?: Event): void {
    if (event) event.preventDefault();
    const host = this.elRef.nativeElement;
    const page = host.querySelector('.intro-page');
    if (page) {
      page.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  ngOnDestroy(): void {
    this.revealObserver?.disconnect();
    this.countObserver?.disconnect();
    this.timeouts.forEach((t) => clearTimeout(t));
  }
}
