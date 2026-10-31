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

  // Raw data from service (only active in_progress classes for Học phần hiện tại)
  classes = computed(() => this.classService.classes().filter(c => c.status === 'in_progress'));

  // Stats computed
  stats = computed(() => {
    const list = this.classes();
    return {
      active: list.length,
      totalStudents: list.reduce((sum, c) => sum + (c.student_total || 0), 0),
      openSubmissions: list.filter(c => c.allow_practice_submission || c.allow_exam_submission).length,
      gradeLocked: list.filter(c => c.is_grade_locked).length
    };
  });

  // Filtered active classes
  filteredClasses = computed(() => {
    let result = this.classes();

    // Filter by keyword
    const keyword = this.searchKeyword().toLowerCase().trim();
    if (keyword) {
      result = result.filter(
        c =>
          c.name.toLowerCase().includes(keyword) ||
          (c.code && c.code.toLowerCase().includes(keyword)) ||
          (c.sport_name && c.sport_name.toLowerCase().includes(keyword))
      );
    }

    return result;
  });

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

