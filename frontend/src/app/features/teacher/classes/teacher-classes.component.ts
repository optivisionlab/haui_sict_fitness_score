import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideCalendar,
  LucideUsers,
  LucideMapPin,
  LucideCheckCircle2,
  LucideLock,
  LucideClock,
  LucideDumbbell,
  LucideFootprints,
  LucideActivity,
  LucideArrowRight,
  LucideBookOpen
} from '@lucide/angular';
import { SearchInputComponent, SelectComponent, SelectOption } from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import { TeacherClass, ClassStatus } from '../models/teacher.model';

@Component({
  selector: 'app-teacher-classes',
  standalone: true,
  imports: [
    CommonModule,
    LucideCalendar,
    LucideUsers,
    LucideMapPin,
    LucideCheckCircle2,
    LucideLock,
    LucideClock,
    LucideDumbbell,
    LucideFootprints,
    LucideActivity,
    LucideArrowRight,
    LucideBookOpen,
    SearchInputComponent,
    SelectComponent
  ],
  templateUrl: './teacher-classes.component.html',
  styleUrl: './teacher-classes.component.scss'
})
export class TeacherClassesComponent {
  private router = inject(Router);
  private classService = inject(TeacherClassService);

  // Filter signals
  searchKeyword = signal<string>('');
  selectedTab = signal<'all' | 'active' | 'pending_finalize' | 'finalized'>('all');
  semesterFilter = signal<string>('all');

  semesterOptions: SelectOption[] = [
    { label: 'Tất cả học kỳ', value: 'all' },
    { label: 'Học kỳ 1 - 2026-2027', value: 'hk1' },
    { label: 'Học kỳ 2 - 2025-2026', value: 'hk2' }
  ];

  // Raw data from service
  classes = this.classService.classes;

  // Stats computed
  stats = computed(() => {
    const list = this.classes();
    return {
      total: list.length,
      active: list.filter(c => c.status === 'active').length,
      pendingFinalize: list.filter(c => c.status === 'pending_finalize').length,
      finalized: list.filter(c => c.status === 'finalized').length,
      totalStudents: list.reduce((sum, c) => sum + c.studentCount, 0)
    };
  });

  // Filtered classes
  filteredClasses = computed(() => {
    let result = this.classes();

    // Filter by tab
    const tab = this.selectedTab();
    if (tab !== 'all') {
      result = result.filter(c => c.status === tab);
    }

    // Filter by keyword
    const keyword = this.searchKeyword().toLowerCase().trim();
    if (keyword) {
      result = result.filter(
        c =>
          c.name.toLowerCase().includes(keyword) ||
          c.code.toLowerCase().includes(keyword) ||
          c.location.toLowerCase().includes(keyword)
      );
    }

    return result;
  });

  setTab(tab: 'all' | 'active' | 'pending_finalize' | 'finalized'): void {
    this.selectedTab.set(tab);
  }

  goToClassDetail(classItem: TeacherClass): void {
    this.router.navigate(['/teacher/classes', classItem.id]);
  }

  getStatusBadgeClass(status: ClassStatus): string {
    switch (status) {
      case 'active':
        return 'badge-processing';
      case 'pending_finalize':
        return 'badge-warning';
      case 'finalized':
        return 'badge-good';
      default:
        return 'badge-muted';
    }
  }

  getStatusText(status: ClassStatus): string {
    switch (status) {
      case 'active':
        return 'Đang diễn ra';
      case 'pending_finalize':
        return 'Chờ chốt điểm';
      case 'finalized':
        return 'Đã chốt điểm';
      default:
        return status;
    }
  }
}
