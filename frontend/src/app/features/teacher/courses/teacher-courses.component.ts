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
  LucideChevronRight,
  LucideFilter,
  LucideRotateCcw,
  LucideLayoutGrid,
  LucideLayers
} from '@lucide/angular';
import { SearchInputComponent, SelectComponent, SelectOption } from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import { TeacherCourseItem, TeacherSemesterSummary, ClassStatus } from '../models/teacher.model';
import { PHYSICAL_SUBJECTS } from '../../../core/constants/academic.constant';

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
    LucideFilter,
    LucideRotateCcw,
    LucideLayoutGrid,
    LucideLayers,
    SearchInputComponent,
    SelectComponent
  ],
  templateUrl: './teacher-courses.component.html',
  styleUrl: './teacher-courses.component.scss'
})
export class TeacherCoursesComponent implements OnInit {
  private router = inject(Router);
  private classService = inject(TeacherClassService);

  // View Mode: 'flat' (xem danh sách trực tiếp kèm filter) | 'tree' (xem phân cấp Kỳ -> Môn -> Lớp)
  viewMode = signal<'flat' | 'tree'>('flat');

  // Drill-down level (khi ở chế độ tree): 'semester' -> 'sport' -> 'class'
  currentLevel = signal<'semester' | 'sport' | 'class'>('semester');

  // Filter Signals
  selectedSemesterFilter = signal<string>('all');
  selectedSportFilter = signal<string>('all');
  selectedStatusFilter = signal<string>('all');
  searchKeyword = signal<string>('');

  // Selected values trong tree drill-down
  selectedSemesterCode = signal<string | null>(null);
  selectedSemesterName = signal<string>('');
  selectedSportName = signal<string | null>(null);

  // Loading states
  isLoading = signal<boolean>(false);
  isLoadingTreeClasses = signal<boolean>(false);

  // Raw data states
  allClasses = signal<TeacherCourseItem[]>([]);
  semesters = signal<TeacherSemesterSummary[]>([]);
  treeSemesterClasses = signal<TeacherCourseItem[]>([]);

  // Filter options từ backend
  backendFilterOptions = signal<{
    semesters: { code: string; name: string }[];
    sports: { code: string; name: string }[];
  }>({ semesters: [], sports: [] });

  // Status options cố định
  readonly statusOptions: SelectOption[] = [
    { label: 'Tất cả trạng thái', value: 'all' },
    { label: 'Đang diễn ra', value: 'in_progress' },
    { label: 'Đã kết thúc', value: 'completed' }
  ];

  ngOnInit(): void {
    this.loadInitialData();
  }

  loadInitialData(): void {
    this.isLoading.set(true);

    // 1. Nạp danh mục kỳ và môn thực tế
    this.classService.loadFilterOptions().subscribe({
      next: (opts) => this.backendFilterOptions.set(opts)
    });

    // 2. Nạp toàn bộ lớp học phần của giảng viên cho chế độ flat view
    this.classService.loadTeacherClasses().subscribe({
      next: (classes) => {
        this.allClasses.set(classes);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });

    // 3. Nạp danh sách kỳ học cho chế độ tree view
    this.classService.loadTeacherSemesters().subscribe({
      next: (sems) => this.semesters.set(sems)
    });
  }

  // Options chọn Học kỳ
  semesterOptions = computed<SelectOption[]>(() => {
    const list = this.backendFilterOptions().semesters;
    const base: SelectOption[] = [{ label: 'Tất cả học kỳ', value: 'all' }];

    if (list && list.length > 0) {
      list.forEach((s) => base.push({ label: s.name, value: s.code }));
    } else {
      // Fallback từ semesters() nếu API filters chưa kịp nạp
      this.semesters().forEach((s) => base.push({ label: s.name, value: s.code }));
    }
    return base;
  });

  // Options chọn Bộ môn thể chất
  sportOptions = computed<SelectOption[]>(() => {
    const base: SelectOption[] = [{ label: 'Tất cả môn học', value: 'all' }];
    const list = this.backendFilterOptions().sports;

    if (list && list.length > 0) {
      list.forEach((sp) => base.push({ label: sp.name, value: sp.code }));
    } else {
      // Fallback danh sách môn chuẩn hệ thống
      PHYSICAL_SUBJECTS.forEach((p) => base.push({ label: p.name, value: p.code }));
    }
    return base;
  });

  // Số lượng bộ lọc đang active
  activeFiltersCount = computed(() => {
    let count = 0;
    if (this.selectedSemesterFilter() !== 'all') count++;
    if (this.selectedSportFilter() !== 'all') count++;
    if (this.selectedStatusFilter() !== 'all') count++;
    if (this.searchKeyword().trim()) count++;
    return count;
  });

  // 1. Chế độ FLAT: Lọc toàn bộ danh sách lớp
  filteredFlatClasses = computed(() => {
    let result = this.allClasses();
    const sem = this.selectedSemesterFilter();
    const sport = this.selectedSportFilter();
    const status = this.selectedStatusFilter();
    const kw = this.searchKeyword().toLowerCase().trim();

    // Lọc theo kỳ
    if (sem && sem !== 'all') {
      result = result.filter((c) => c.semester === sem);
    }

    // Lọc theo môn
    if (sport && sport !== 'all') {
      result = result.filter(
        (c) =>
          (c.sport_code && c.sport_code.toUpperCase() === sport.toUpperCase()) ||
          (c.sport_name && c.sport_name.toLowerCase() === sport.toLowerCase())
      );
    }

    // Lọc theo trạng thái
    if (status && status !== 'all') {
      result = result.filter((c) => c.status === status);
    }

    // Lọc theo từ khóa
    if (kw) {
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(kw) ||
          (c.code && c.code.toLowerCase().includes(kw)) ||
          (c.sport_name && c.sport_name.toLowerCase().includes(kw)) ||
          (c.semester_name && c.semester_name.toLowerCase().includes(kw))
      );
    }

    return result;
  });

  // Reset toàn bộ bộ lọc
  resetFilters(): void {
    this.selectedSemesterFilter.set('all');
    this.selectedSportFilter.set('all');
    this.selectedStatusFilter.set('all');
    this.searchKeyword.set('');
  }

  // Chuyển đổi View Mode
  setViewMode(mode: 'flat' | 'tree'): void {
    this.viewMode.set(mode);
    if (mode === 'tree') {
      this.currentLevel.set('semester');
      this.selectedSemesterCode.set(null);
      this.selectedSportName.set(null);
    }
  }

  // 2. Chế độ TREE: Xử lý drill-down
  filteredSemesters = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    const list = this.semesters();
    if (!kw) return list;
    return list.filter(
      (s) => s.name.toLowerCase().includes(kw) || s.code.toLowerCase().includes(kw)
    );
  });

  sportsList = computed<SportViewItem[]>(() => {
    const list = this.treeSemesterClasses();
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
      const activeClasses = val.classes.filter((c) => c.status === 'in_progress').length;
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

  filteredSports = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    if (!kw) return this.sportsList();
    return this.sportsList().filter(
      (s) => s.name.toLowerCase().includes(kw) || s.code.toLowerCase().includes(kw)
    );
  });

  classesInSport = computed<TeacherCourseItem[]>(() => {
    const sport = this.selectedSportName();
    if (!sport) return [];
    return this.treeSemesterClasses().filter(
      (c) => (c.sport_name || 'Giáo dục Thể chất') === sport
    );
  });

  filteredTreeClasses = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    const list = this.classesInSport();
    if (!kw) return list;
    return list.filter(
      (c) =>
        c.name.toLowerCase().includes(kw) || (c.code && c.code.toLowerCase().includes(kw))
    );
  });

  // Tree Navigation
  selectSemester(sem: TeacherSemesterSummary): void {
    this.selectedSemesterCode.set(sem.code);
    this.selectedSemesterName.set(sem.name);
    this.searchKeyword.set('');
    this.currentLevel.set('sport');

    this.isLoadingTreeClasses.set(true);
    this.treeSemesterClasses.set([]);
    this.classService.loadCoursesBySemester(sem.code).subscribe({
      next: (classes) => {
        this.treeSemesterClasses.set(classes);
        this.isLoadingTreeClasses.set(false);
      },
      error: () => this.isLoadingTreeClasses.set(false)
    });
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
