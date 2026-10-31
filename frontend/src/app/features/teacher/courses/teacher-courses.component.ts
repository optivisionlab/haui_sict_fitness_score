import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideCalendar,
  LucideUsers,
  LucideCheckCircle2,
  LucideClock,
  LucideActivity,
  LucideArrowRight,
  LucideArrowLeft,
  LucideBookOpen,
  LucideTrophy,
  LucideChevronRight
} from '@lucide/angular';
import { SearchInputComponent } from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import { TeacherCourseItem, TeacherSemesterSummary, ClassStatus } from '../models/teacher.model';

export interface SportViewItem {
  name: string;
  code: string;
  totalClasses: number;
  totalStudents: number;
  activeClasses: number;
}

@Component({
  selector: 'app-teacher-courses',
  standalone: true,
  imports: [
    CommonModule,
    LucideCalendar,
    LucideUsers,
    LucideCheckCircle2,
    LucideClock,
    LucideActivity,
    LucideArrowRight,
    LucideArrowLeft,
    LucideBookOpen,
    LucideTrophy,
    LucideChevronRight,
    SearchInputComponent
  ],
  templateUrl: './teacher-courses.component.html',
  styleUrl: './teacher-courses.component.scss'
})
export class TeacherCoursesComponent implements OnInit {
  private router = inject(Router);
  private classService = inject(TeacherClassService);

  // Drill-down level: 'semester' -> 'sport' -> 'class'
  currentLevel = signal<'semester' | 'sport' | 'class'>('semester');

  // Selected values
  selectedSemesterCode = signal<string | null>(null);
  selectedSemesterName = signal<string>('');
  selectedSportName = signal<string | null>(null);

  // Search filter
  searchKeyword = signal<string>('');

  // Loading states
  isLoadingSemesters = signal<boolean>(false);
  isLoadingClasses = signal<boolean>(false);

  // Data states (Lazy loaded on demand)
  semesters = signal<TeacherSemesterSummary[]>([]);
  semesterClasses = signal<TeacherCourseItem[]>([]);

  ngOnInit(): void {
    this.loadSemesters();
  }

  /**
   * Tải danh sách tóm tắt các kỳ học (chỉ tải metadata và số liệu đếm, không kéo lớp)
   */
  loadSemesters(): void {
    this.isLoadingSemesters.set(true);
    this.classService.loadTeacherSemesters().subscribe({
      next: (list) => {
        this.semesters.set(list);
        this.isLoadingSemesters.set(false);
      },
      error: () => {
        this.isLoadingSemesters.set(false);
      }
    });
  }

  /**
   * Kéo danh sách lớp học phần khi người dùng click vào kỳ cụ thể
   */
  loadClassesForSemester(semesterCode: string): void {
    this.isLoadingClasses.set(true);
    this.semesterClasses.set([]);
    this.classService.loadCoursesBySemester(semesterCode).subscribe({
      next: (classes) => {
        this.semesterClasses.set(classes);
        this.isLoadingClasses.set(false);
      },
      error: () => {
        this.isLoadingClasses.set(false);
      }
    });
  }

  // 1. Filtered Semesters by search
  filteredSemesters = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    const list = this.semesters();
    if (!kw) return list;
    return list.filter(s =>
      s.name.toLowerCase().includes(kw) || s.code.toLowerCase().includes(kw)
    );
  });

  // 2. Grouped Sports for selected semester (computed from lazily loaded semesterClasses)
  sportsList = computed<SportViewItem[]>(() => {
    const list = this.semesterClasses();
    const map = new Map<string, { code: string; classes: TeacherCourseItem[] }>();

    for (const c of list) {
      const sportName = c.sport_name || 'Giáo dục Thể chất';
      const sportCode = c.sport_code || 'GENERAL';

      if (!map.has(sportName)) {
        map.set(sportName, { code: sportCode, classes: [] });
      }
      map.get(sportName)!.classes.push(c);
    }

    const result: SportViewItem[] = [];
    map.forEach((val, name) => {
      const totalStudents = val.classes.reduce((sum, c) => sum + (c.student_total || 0), 0);
      const activeClasses = val.classes.filter(c => c.status === 'in_progress').length;
      result.push({
        name,
        code: val.code,
        totalClasses: val.classes.length,
        totalStudents,
        activeClasses
      });
    });

    return result.sort((a, b) => b.totalClasses - a.totalClasses);
  });

  // Filtered Sports by search
  filteredSports = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    if (!kw) return this.sportsList();
    return this.sportsList().filter(s =>
      s.name.toLowerCase().includes(kw) || s.code.toLowerCase().includes(kw)
    );
  });

  // 3. Classes in selected semester and sport
  classesInSport = computed<TeacherCourseItem[]>(() => {
    const sport = this.selectedSportName();
    if (!sport) return [];

    return this.semesterClasses().filter(c => (c.sport_name || 'Giáo dục Thể chất') === sport);
  });

  // Filtered Classes by search
  filteredClasses = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    const list = this.classesInSport();
    if (!kw) return list;
    return list.filter(c =>
      c.name.toLowerCase().includes(kw) ||
      (c.code && c.code.toLowerCase().includes(kw))
    );
  });

  // Navigation actions
  selectSemester(sem: TeacherSemesterSummary): void {
    this.selectedSemesterCode.set(sem.code);
    this.selectedSemesterName.set(sem.name);
    this.searchKeyword.set('');
    this.currentLevel.set('sport');
    this.loadClassesForSemester(sem.code);
  }

  selectSport(sport: SportViewItem): void {
    this.selectedSportName.set(sport.name);
    this.searchKeyword.set('');
    this.currentLevel.set('class');
  }

  goToSemesterLevel(): void {
    this.selectedSemesterCode.set(null);
    this.selectedSemesterName.set('');
    this.selectedSportName.set(null);
    this.searchKeyword.set('');
    this.currentLevel.set('semester');
  }

  goToSportLevel(): void {
    this.selectedSportName.set(null);
    this.searchKeyword.set('');
    this.currentLevel.set('sport');
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
        return 'Chưa bắt đầu';
    }
  }
}
