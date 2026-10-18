import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideCalendar,
  LucideUsers,
  LucideCheckCircle2,
  LucideClock,
  LucideActivity,
  LucideArrowRight,
  LucideBookOpen
} from '@lucide/angular';
import { SearchInputComponent, SelectOption } from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import { TeacherCourseItem, ClassStatus } from '../models/teacher.model';

@Component({
  selector: 'app-teacher-classes',
  standalone: true,
  imports: [
    CommonModule,
    LucideCalendar,
    LucideUsers,
    LucideCheckCircle2,
    LucideClock,
    LucideActivity,
    LucideArrowRight,
    LucideBookOpen,
    SearchInputComponent
  ],
  templateUrl: './teacher-classes.component.html',
  styleUrl: './teacher-classes.component.scss'
})
export class TeacherClassesComponent {
  private router = inject(Router);
  private classService = inject(TeacherClassService);

  // Filter signals
  searchKeyword = signal<string>('');
  selectedTab = signal<'all' | 'in_progress' | 'completed'>('all');

  // Raw data from service
  classes = this.classService.classes;

  // Stats computed
  stats = computed(() => {
    const list = this.classes();
    return {
      total: list.length,
      active: list.filter(c => c.status === 'in_progress').length,
      finalized: list.filter(c => c.status === 'completed').length,
      totalStudents: list.reduce((sum, c) => sum + (c.student_total || 0), 0)
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
          (c.code && c.code.toLowerCase().includes(keyword))
      );
    }

    return result;
  });

  setTab(tab: 'all' | 'in_progress' | 'completed'): void {
    this.selectedTab.set(tab);
  }

  goToClassDetail(classItem: TeacherCourseItem): void {
    this.router.navigate(['/teacher/classes', classItem.id]);
  }

  getStatusBadgeClass(status: ClassStatus): string {
    switch (status) {
      case 'in_progress':
        return 'badge-processing';
      case 'completed':
        return 'badge-good';
      default:
        return 'badge-muted';
    }
  }

  getStatusText(status: ClassStatus): string {
    switch (status) {
      case 'in_progress':
        return 'Đang diễn ra';
      case 'completed':
        return 'Đã kết thúc';
      default:
        return status;
    }
  }
}

