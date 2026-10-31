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
  LucideGraduationCap,
  LucideTrophy,
  LucideChevronRight,
  LucideLayers
} from '@lucide/angular';
import { SearchInputComponent } from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import { TeacherCourseItem, ClassStatus } from '../models/teacher.model';

export interface SemesterViewItem {
  code: string;
  name: string;
  academic_year: string;
  term: number;
  totalSports: number;
  totalClasses: number;
  totalStudents: number;
  activeClasses: number;
  is_current: boolean;
}

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
    LucideGraduationCap,
    LucideTrophy,
    LucideChevronRight,
    LucideLayers,
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

  // Raw data from service
  classes = this.classService.classes;

  ngOnInit(): void {
    // If needed, can reload or sync
  }

  // 1. Grouped Semesters
  semestersList = computed<SemesterViewItem[]>(() => {
    const list = this.classes();
    const map = new Map<string, {
      name: string;
      academic_year: string;
      term: number;
      sports: Set<string>;
      classes: TeacherCourseItem[];
    }>();

    for (const c of list) {
      const semCode = c.semester || '2026-2027.1';
      const semName = c.semester_name || 'Học kỳ 1 (2026 - 2027)';
      const year = c.academic_year || '2026-2027';
      const term = c.term || 1;

      if (!map.has(semCode)) {
        map.set(semCode, {
          name: semName,
          academic_year: year,
          term,
          sports: new Set<string>(),
          classes: []
        });
      }

      const item = map.get(semCode)!;
      item.classes.push(c);
      if (c.sport_name) {
        item.sports.add(c.sport_name);
      }
    }

    const result: SemesterViewItem[] = [];
    map.forEach((val, code) => {
      const totalStudents = val.classes.reduce((sum, c) => sum + (c.student_total || 0), 0);
      const activeClasses = val.classes.filter(c => c.status === 'in_progress').length;
      result.push({
        code,
        name: val.name,
        academic_year: val.academic_year,
        term: val.term,
        totalSports: Math.max(val.sports.size, 1),
        totalClasses: val.classes.length,
        totalStudents,
        activeClasses,
        is_current: activeClasses > 0
      });
    });

    // Sort: current semester first, then newest academic year
    return result.sort((a, b) => {
      if (a.is_current && !b.is_current) return -1;
      if (!a.is_current && b.is_current) return 1;
      return b.code.localeCompare(a.code);
    });
  });

  // Filtered Semesters by search
  filteredSemesters = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    if (!kw) return this.semestersList();
    return this.semestersList().filter(s =>
      s.name.toLowerCase().includes(kw) || s.code.toLowerCase().includes(kw)
    );
  });

  // 2. Grouped Sports for selected semester
  sportsList = computed<SportViewItem[]>(() => {
    const sem = this.selectedSemesterCode();
    if (!sem) return [];

    const list = this.classes().filter(c => (c.semester || '2026-2027.1') === sem);
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
    const sem = this.selectedSemesterCode();
    const sport = this.selectedSportName();
    if (!sem || !sport) return [];

    return this.classes().filter(c => {
      const matchSem = (c.semester || '2026-2027.1') === sem;
      const matchSport = (c.sport_name || 'Giáo dục Thể chất') === sport;
      return matchSem && matchSport;
    });
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
  selectSemester(sem: SemesterViewItem): void {
    this.selectedSemesterCode.set(sem.code);
    this.selectedSemesterName.set(sem.name);
    this.searchKeyword.set('');
    this.currentLevel.set('sport');
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
