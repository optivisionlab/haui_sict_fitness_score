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
        const items = res?.data?.items || [];
        if (items.length > 0) {
          const mapped: GradeSubject[] = items.map((e: any, idx: number) => {
            const isEligible = (e.grades?.attendanceScore ?? 0) >= 5.0 && (e.grades?.processScore === null || e.grades?.processScore >= 4.0);
            return {
              id: e.courseId || `sub-${idx}`,
              name: e.courseName || 'Giáo dục Thể chất',
              classCode: e.courseId.substring(0, 10).toUpperCase(),
              startDate: '01/09/2026',
              regularGradeDeadline: '20/11/2026',
              regularScore: e.grades?.processScore ?? e.grades?.attendanceScore ?? null,
              score: e.grades?.finalScore ?? null,
              letterGrade: e.grades?.letterGrade ?? null,
              liveClassCompleted: 15,
              practiceCompleted: Math.round(e.progressPercent || 0),
              testCompleted: e.grades?.examScore ? 'Đã thi' : 'Chưa thi',
              examCondition: isEligible ? 'eligible' : 'ineligible',
              status: e.status === 'active' ? 'active' : 'completed',
              weeklyDetails: [
                { week: 'Tuần 1', period: '01/09 - 07/09', practiceCompleted: 100, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
                { week: 'Tuần 2', period: '08/09 - 14/09', practiceCompleted: 100, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
                { week: 'Tuần 3', period: '15/09 - 21/09', practiceCompleted: 80, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
                { week: 'Tuần 4', period: '22/09 - 28/09', practiceCompleted: 90, liveClassCompleted: 1, testCompleted: '', examCondition: '' }
              ],
              summary: {
                period: '01/09/2026 - 20/11/2026',
                practiceCompleted: `${Math.round(e.progressPercent || 0)}%`,
                liveClassCompleted: '15/15',
                testCompleted: e.grades?.examScore ? '1/1' : '0/1',
                examCondition: isEligible ? 'Đủ điều kiện' : 'Không đủ điều kiện'
              }
            };
          });
          this.subjects.set(mapped);
        }
      },
      error: () => {}
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
  }

  backToList(): void {
    this.activeView.set('list');
    this.selectedSubject.set(null);
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
