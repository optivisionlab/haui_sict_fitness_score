import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import {
  LucideLayoutDashboard,
  LucideUsers,
  LucideGraduationCap,
  LucideLogOut,
  LucideArrowRightLeft,
  LucideShieldCheck
} from '@lucide/angular';

@Component({
  selector: 'app-admin-sidebar',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterLinkActive,
    LucideLayoutDashboard,
    LucideUsers,
    LucideGraduationCap,
    LucideLogOut,
    LucideArrowRightLeft,
    LucideShieldCheck
  ],
  templateUrl: './admin-sidebar.component.html',
  styleUrl: './admin-sidebar.component.scss'
})
export class AdminSidebarComponent {
  constructor(private router: Router) {}

  onLogout(): void {
    this.router.navigate(['/login']);
  }
}
