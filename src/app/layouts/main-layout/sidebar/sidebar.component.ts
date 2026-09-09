import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import {
  LucideHome,
  LucideGraduationCap,
  LucideBell,
  LucideUser,
  LucideChartNoAxesColumn,
  LucideLogOut
} from '@lucide/angular';

interface NavItem {
  label: string;
  route: string;
  icon: any;
  extraMarginTop?: boolean;
}

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
    LucideLogOut
  ],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {
  navItems = [
    { label: 'Trang chủ', route: '/student/home', icon: 'home' },
    { label: 'Khóa học của tôi', route: '/student/courses', icon: 'courses' },
    { label: 'Thông báo', route: '/student/notifications', icon: 'notifications' },
    { label: 'Thông tin cá nhân', route: '/student/profile', icon: 'profile' },
    { label: 'Kết quả học tập', route: '/student/grades', icon: 'grades', extraMarginTop: true },
  ];

  constructor(private router: Router) {}

  onLogout(): void {
    this.router.navigate(['/login']);
  }
}
