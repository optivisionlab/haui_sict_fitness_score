import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideArrowLeft } from '@lucide/angular';
import { SearchInputComponent, PaginationComponent, SelectComponent, SelectOption } from '@shared/components';
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
export class GradesComponent {
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

  // Mock Data
  subjects = signal<GradeSubject[]>([
    {
      id: 'sub-1',
      name: 'Ngữ âm - Âm vị học',
      classCode: '20254FL6071_TX002',
      startDate: '26/07/2026',
      regularGradeDeadline: '20/09/2026',
      liveClassCompleted: 2,
      practiceCompleted: 28,
      testCompleted: '',
      examCondition: 'eligible',
      status: 'active',
      weeklyDetails: [
        { week: 'Tuần 1', period: '26/07/2026 - 02/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 2', period: '03/08/2026 - 09/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 3', period: '10/08/2026 - 16/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 4', period: '17/08/2026 - 23/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 5', period: '24/08/2026 - 30/08/2026', practiceCompleted: 28, liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 6', period: '31/08/2026 - 06/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 7', period: '07/09/2026 - 13/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 8', period: '14/09/2026 - 20/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' }
      ],
      summary: {
        period: '26/07/2026 - 20/09/2026',
        practiceCompleted: '28/28',
        liveClassCompleted: '2/2',
        testCompleted: '0/0',
        examCondition: 'Đủ điều kiện'
      }
    },
    {
      id: 'sub-2',
      name: 'Biên dịch tiếng Anh Du lịch-Thương mại 2',
      classCode: '20254FL6081_TX002',
      startDate: '26/07/2026',
      regularGradeDeadline: '20/09/2026',
      liveClassCompleted: 2,
      practiceCompleted: 20,
      testCompleted: '',
      examCondition: null,
      status: 'active',
      weeklyDetails: [
        { week: 'Tuần 1', period: '26/07/2026 - 02/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 2', period: '03/08/2026 - 09/08/2026', practiceCompleted: 10, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
        { week: 'Tuần 3', period: '10/08/2026 - 16/08/2026', practiceCompleted: 10, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
        { week: 'Tuần 4', period: '17/08/2026 - 23/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 5', period: '24/08/2026 - 30/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 6', period: '31/08/2026 - 06/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 7', period: '07/09/2026 - 13/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 8', period: '14/09/2026 - 20/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' }
      ],
      summary: {
        period: '26/07/2026 - 20/09/2026',
        practiceCompleted: '20/28',
        liveClassCompleted: '2/2',
        testCompleted: '0/0',
        examCondition: ''
      }
    },
    {
      id: 'sub-3',
      name: 'Phiên dịch tiếng Anh Du lịch-Thương mại 2',
      classCode: '20254FL6082_TX002',
      startDate: '26/07/2026',
      regularGradeDeadline: '20/09/2026',
      liveClassCompleted: 2,
      practiceCompleted: 10,
      testCompleted: '',
      examCondition: null,
      status: 'active',
      weeklyDetails: [
        { week: 'Tuần 1', period: '26/07/2026 - 02/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 2', period: '03/08/2026 - 09/08/2026', practiceCompleted: '', liveClassCompleted: 1, testCompleted: '', examCondition: '' },
        { week: 'Tuần 3', period: '10/08/2026 - 16/08/2026', practiceCompleted: 10, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
        { week: 'Tuần 4', period: '17/08/2026 - 23/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 5', period: '24/08/2026 - 30/08/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 6', period: '31/08/2026 - 06/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 7', period: '07/09/2026 - 13/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' },
        { week: 'Tuần 8', period: '14/09/2026 - 20/09/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' }
      ],
      summary: {
        period: '26/07/2026 - 20/09/2026',
        practiceCompleted: '10/28',
        liveClassCompleted: '2/2',
        testCompleted: '0/0',
        examCondition: ''
      }
    },
    {
      id: 'sub-4',
      name: 'Tiếng Anh chuyên ngành Công nghệ thông tin',
      classCode: '20254IT6011_TX001',
      startDate: '01/06/2026',
      regularGradeDeadline: '15/08/2026',
      liveClassCompleted: 4,
      practiceCompleted: 35,
      testCompleted: 2,
      examCondition: 'eligible',
      status: 'completed',
      weeklyDetails: [
        { week: 'Tuần 1', period: '01/06/2026 - 08/06/2026', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
        { week: 'Tuần 2', period: '09/06/2026 - 16/06/2026', practiceCompleted: 10, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
        { week: 'Tuần 3', period: '17/06/2026 - 24/06/2026', practiceCompleted: 10, liveClassCompleted: 1, testCompleted: 1, examCondition: '' },
        { week: 'Tuần 4', period: '25/06/2026 - 02/07/2026', practiceCompleted: 10, liveClassCompleted: 1, testCompleted: 1, examCondition: '' }
      ],
      summary: {
        period: '01/06/2026 - 15/08/2026',
        practiceCompleted: '35/35',
        liveClassCompleted: '4/4',
        testCompleted: '2/2',
        examCondition: 'Đủ điều kiện'
      }
    },
    {
      id: 'sub-5',
      name: 'Kỹ năng giao tiếp trong môi trường quốc tế',
      classCode: '20254FL6090_TX003',
      startDate: '01/06/2026',
      regularGradeDeadline: '15/08/2026',
      liveClassCompleted: 1,
      practiceCompleted: 8,
      testCompleted: 0,
      examCondition: 'ineligible',
      status: 'completed',
      weeklyDetails: [
        { week: 'Tuần 1', period: '01/06/2026 - 08/06/2026', practiceCompleted: 8, liveClassCompleted: 1, testCompleted: '', examCondition: '' },
        { week: 'Tuần 2', period: '09/06/2026 - 16/06/2026', practiceCompleted: '', liveClassCompleted: '', testCompleted: '', examCondition: '' }
      ],
      summary: {
        period: '01/06/2026 - 15/08/2026',
        practiceCompleted: '8/30',
        liveClassCompleted: '1/4',
        testCompleted: '0/2',
        examCondition: 'Không đủ điều kiện'
      }
    }
  ]);

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
}
