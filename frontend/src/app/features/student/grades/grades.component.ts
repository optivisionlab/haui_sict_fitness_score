import { Component, signal, computed, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { LucideArrowLeft } from '@lucide/angular';
import { SearchInputComponent, PaginationComponent, SelectComponent, SelectOption } from '@shared/components';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/auth.model';
import { GradeSubject } from './models/grade.model';

@Component({
  selector: 'app-grades',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideArrowLeft,
    SearchInputComponent,
    PaginationComponent,
    SelectComponent
  ],
  templateUrl: './grades.component.html',
  styleUrl: './grades.component.scss'
})
export class GradesComponent implements OnInit {
  private http = inject(HttpClient);

  // Views: 'list' or 'detail'
  activeView = signal<'list' | 'detail'>('list');
  selectedSubject = signal<GradeSubject | null>(null);
  selectedSubjectGrades = signal<any>(null);
  selectedSubjectTasks = signal<any[]>([]);
  isLoadingDetail = signal<boolean>(false);

  // Filter options for dropdowns
  statusOptions: SelectOption[] = [
    { label: 'Tất cả', value: 'all' },
    { label: 'Đang học', value: 'active' },
    { label: 'Hoàn thành', value: 'completed' }
  ];

  conditionOptions: SelectOption[] = [
    { label: 'Tất cả', value: 'all' },
    { label: 'Đủ điều kiện', value: 'eligible' },
    { label: 'Không đủ điều kiện', value: 'ineligible' }
  ];

  // Filters
  searchKeyword = signal<string>('');
  statusFilter = signal<string>('all');
  conditionFilter = signal<string>('all');

  // Pagination
  currentPage = signal<number>(1);
  pageSize = signal<number>(4);

  // Subjects list from database API
  subjects = signal<GradeSubject[]>([]);

  ngOnInit(): void {
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/enrollments/my-courses`).subscribe({
      next: (res) => {
        const items = res?.data?.items || (Array.isArray(res?.data) ? res.data : []);
        if (items.length > 0) {
          const mapped: GradeSubject[] = items.map((e: any, idx: number) => {
            const courseId = e.courseId || e.id || `sub-${idx}`;
            const isEligible = (e.grades?.attendanceScore ?? 0) >= 5.0 && (e.grades?.processScore === null || e.grades?.processScore >= 4.0);
            const createdDate = e.createdAt ? new Date(e.createdAt).toLocaleDateString('vi-VN') : 'Chưa cập nhật';
            return {
              id: courseId,
              name: e.courseName || e.name || 'Giáo dục Thể chất',
              classCode: courseId.substring(0, 10).toUpperCase(),
              startDate: createdDate,
              regularGradeDeadline: 'Chưa cập nhật',
              regularScore: e.grades?.processScore ?? e.grades?.attendanceScore ?? null,
              score: e.grades?.finalScore ?? null,
              letterGrade: e.grades?.letterGrade ?? null,
              liveClassCompleted: e.grades?.attendanceScore !== null && e.grades?.attendanceScore !== undefined ? e.grades.attendanceScore : 0,
              practiceCompleted: Math.round(e.progressPercent || 0),
              testCompleted: e.grades?.examScore ? 'Đã thi' : 'Chưa thi',
              examCondition: isEligible ? 'eligible' : 'ineligible',
              status: e.status === 'active' ? 'active' : 'completed',
              weeklyDetails: [],
              summary: {
                period: 'Học kỳ hiện tại',
                practiceCompleted: `${Math.round(e.progressPercent || 0)}%`,
                liveClassCompleted: e.grades?.attendanceScore !== null && e.grades?.attendanceScore !== undefined ? `${e.grades.attendanceScore} đ` : 'Chưa có',
                testCompleted: e.grades?.examScore !== null && e.grades?.examScore !== undefined ? `${e.grades.examScore} đ` : (e.grades?.processScore !== null && e.grades?.processScore !== undefined ? `${e.grades.processScore} đ` : 'Chưa có'),
                examCondition: isEligible ? 'Đủ điều kiện' : 'Không đủ điều kiện'
              }
            };
          });
          this.subjects.set(mapped);
        } else {
          this.subjects.set([]);
        }
      },
      error: () => {
        this.subjects.set([]);
      }
    });
  }

  // Filtered subjects
  filteredSubjects = computed(() => {
    const keyword = this.searchKeyword().toLowerCase().trim();
    const status = this.statusFilter();
    const condition = this.conditionFilter();

    return this.subjects().filter((item) => {
      const matchKeyword =
        !keyword ||
        item.name.toLowerCase().includes(keyword) ||
        item.classCode.toLowerCase().includes(keyword);

      const matchStatus =
        status === 'all' || item.status === status;

      const matchCondition =
        condition === 'all' ||
        (condition === 'eligible' && item.examCondition === 'eligible') ||
        (condition === 'ineligible' && item.examCondition === 'ineligible');

      return matchKeyword && matchStatus && matchCondition;
    });
  });

  // Paginated subjects
  paginatedSubjects = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredSubjects().slice(start, start + this.pageSize());
  });

  openDetail(subject: GradeSubject): void {
    this.selectedSubject.set(subject);
    this.activeView.set('detail');
    this.isLoadingDetail.set(true);
    this.selectedSubjectGrades.set(null);
    this.selectedSubjectTasks.set([]);

    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/student/courses/${subject.id}/grades`).subscribe({
      next: (res) => {
        this.isLoadingDetail.set(false);
        const data = res?.data;
        if (data) {
          this.selectedSubjectGrades.set(data);
          this.selectedSubjectTasks.set(data.tasks || []);
        }
      },
      error: () => {
        this.isLoadingDetail.set(false);
      }
    });
  }

  backToList(): void {
    this.activeView.set('list');
    this.selectedSubject.set(null);
    this.selectedSubjectGrades.set(null);
    this.selectedSubjectTasks.set([]);
  }

  formatDate(dateStr?: string | null): string {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    } catch {
      return dateStr;
    }
  }

  getCategoryLabel(category?: string, idx: number = 0): string {
    if (category === 'exam') return 'Thi cuối kỳ';
    if (category === 'midterm') return 'Giữa kỳ';
    return `TX${idx + 1}: Kỹ thuật`;
  }

  getTechnicalEvaluation(score?: number | null): string {
    if (score === null || score === undefined) return 'Chưa nộp video';
    if (score >= 8.5) return 'Kỹ thuật xuất sắc, góc khớp chuẩn';
    if (score >= 7.0) return 'Đạt chuẩn kỹ thuật tốt';
    if (score >= 5.0) return 'Đạt chuẩn kỹ thuật cơ bản';
    return 'Cần rèn luyện thêm biên độ khớp';
  }

  setPage(page: number): void {
    this.currentPage.set(page);
  }

  onFilterChange(): void {
    this.currentPage.set(1);
  }

  getGradeClass(grade?: string | null): string {
    if (!grade) return '';
    const first = grade.charAt(0).toUpperCase();
    switch (first) {
      case 'A': return 'grade-a';
      case 'B': return 'grade-b';
      case 'C': return 'grade-c';
      case 'D': return 'grade-d';
      case 'F': return 'grade-f';
      default: return '';
    }
  }
}
