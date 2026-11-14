import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import {
  LucideUsers,
  LucideGraduationCap,
  LucideUserCheck,
  LucideTrophy,
  LucideBookOpen,
  LucidePlus,
  LucideArrowRight
} from '@lucide/angular';
import { AdminService, DashboardStats, Course, Sport } from '@core/services/admin.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideUsers,
    LucideGraduationCap,
    LucideUserCheck,
    LucideTrophy,
    LucideBookOpen,
    LucidePlus,
    LucideArrowRight
  ],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.scss'
})
export class AdminDashboardComponent implements OnInit {
  private adminService = inject(AdminService);

  isLoading = signal<boolean>(true);
  stats = signal<DashboardStats>({
    totalUsers: 0,
    totalStudents: 0,
    totalTeachers: 0,
    totalSports: 0,
    totalCourses: 0
  });

  recentCourses = signal<Course[]>([]);
  recentSports = signal<Sport[]>([]);

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);

    this.adminService.getDashboardStats().subscribe({
      next: (data) => {
        this.stats.set(data);
      },
      error: () => {}
    });

    this.adminService.getCourses(1, 5).subscribe({
      next: (res) => {
        this.recentCourses.set(res.items || []);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });

    this.adminService.getSports(1, 5).subscribe({
      next: (res) => {
        this.recentSports.set(res.items || []);
      },
      error: () => {}
    });
  }
}
