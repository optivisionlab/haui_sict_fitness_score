import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, NavigationEnd } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs/operators';
import {
  LucideHome,
  LucideGraduationCap,
  LucideBell,
  LucideUser,
  LucideChartNoAxesColumn,
  LucideLogOut,
  LucideBookOpen,
  LucideLayoutDashboard,
  LucideUsers,
  LucideTrophy
} from '@lucide/angular';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterLinkActive,
    LucideHome,
    LucideGraduationCap,
    LucideBell,
    LucideUser,
    LucideChartNoAxesColumn,
    LucideLogOut,
    LucideBookOpen,
    LucideLayoutDashboard,
    LucideUsers,
    LucideTrophy
  ],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {
  private router = inject(Router);
  private authService = inject(AuthService);

  showLogoutConfirm = signal<boolean>(false);

  // Detect current route
  private currentUrl = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map(e => e.urlAfterRedirects)
    ),
    { initialValue: this.router.url }
  );

  isAdmin = computed(() => {
    const url = this.currentUrl();
    return url.startsWith('/admin');
  });

  isTeacher = computed(() => {
    const url = this.currentUrl();
    return url.startsWith('/teacher');
  });

  onLogout(): void {
    this.showLogoutConfirm.set(true);
  }

  cancelLogout(): void {
    this.showLogoutConfirm.set(false);
  }

  confirmLogout(): void {
    this.showLogoutConfirm.set(false);
    this.authService.logout();
  }
}
