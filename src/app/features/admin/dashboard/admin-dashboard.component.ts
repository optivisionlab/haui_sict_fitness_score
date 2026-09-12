import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import {
  LucideUsers,
  LucideGraduationCap,
  LucideCheckCircle2,
  LucideAlertTriangle,
  LucideArrowRight
} from '@lucide/angular';
import { PaginationComponent } from '@shared/components';
import { AdminDataService } from '../services/admin-data.service';
import { AdminCourseClass, AdminStudentItem } from '../models/admin.model';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideUsers,
    LucideGraduationCap,
    LucideCheckCircle2,
    LucideAlertTriangle,
    LucideArrowRight,
    PaginationComponent
  ],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.scss'
})
export class AdminDashboardComponent {
  protected readonly Math = Math;
  adminService = inject(AdminDataService);

  // KPIs
  kpis = this.adminService.kpis;

  // Table 1: Classes pagination
  classPage = signal<number>(1);
  classPageSize = signal<number>(4);

  classes = this.adminService.classes;
  paginatedClasses = computed(() => {
    const start = (this.classPage() - 1) * this.classPageSize();
    return this.classes().slice(start, start + this.classPageSize());
  });

  // Table 2: Alert students (ineligible or pending)
  alertPage = signal<number>(1);
  alertPageSize = signal<number>(4);

  alertStudents = computed(() => {
    return this.adminService.students().filter(
      (s) => s.examCondition === 'ineligible' || s.examCondition === 'pending'
    );
  });

  paginatedAlertStudents = computed(() => {
    const start = (this.alertPage() - 1) * this.alertPageSize();
    return this.alertStudents().slice(start, start + this.alertPageSize());
  });

  setClassPage(page: number): void {
    this.classPage.set(page);
  }

  setAlertPage(page: number): void {
    this.alertPage.set(page);
  }
}
