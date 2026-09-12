import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideArrowLeft,
  LucideDownload,
  LucideCheckCircle2,
  LucideEye
} from '@lucide/angular';
import {
  SearchInputComponent,
  PaginationComponent,
  SelectComponent,
  SelectOption
} from '@shared/components';
import { AdminDataService } from '../services/admin-data.service';
import { AdminStudentItem, ExamConditionType } from '../models/admin.model';

@Component({
  selector: 'app-admin-students',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideArrowLeft,
    LucideDownload,
    LucideCheckCircle2,
    LucideEye,
    SearchInputComponent,
    PaginationComponent,
    SelectComponent
  ],
  templateUrl: './admin-students.component.html',
  styleUrl: './admin-students.component.scss'
})
export class AdminStudentsComponent {
  private adminService = inject(AdminDataService);

  // Active view: 'list' or 'detail'
  activeView = signal<'list' | 'detail'>('list');
  selectedStudent = signal<AdminStudentItem | null>(null);

  // Edit condition state in detail view
  editCondition = signal<ExamConditionType>('eligible');
  editConditionNote = signal<string>('');
  saveSuccessMessage = signal<string>('');

  // Filter options
  conditionOptions: SelectOption[] = [
    { label: 'Tất cả điều kiện', value: 'all' },
    { label: 'Đủ điều kiện', value: 'eligible' },
    { label: 'Không đủ điều kiện', value: 'ineligible' },
    { label: 'Cần bổ sung', value: 'pending' }
  ];

  classFilterOptions = computed<SelectOption[]>(() => {
    const classes = this.adminService.classes();
    const opts: SelectOption[] = [{ label: 'Tất cả lớp học phần', value: 'all' }];
    classes.forEach((c) => {
      opts.push({ label: `${c.classCode} - ${c.subjectName}`, value: c.classCode });
    });
    return opts;
  });

  // Filter values
  searchKeyword = signal<string>('');
  selectedClassFilter = signal<string>('all');
  selectedConditionFilter = signal<string>('all');

  // Pagination using shared component
  currentPage = signal<number>(1);
  pageSize = signal<number>(5);

  // Filtered students list
  filteredStudents = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    const cls = this.selectedClassFilter();
    const cond = this.selectedConditionFilter();

    return this.adminService.students().filter((item) => {
      const matchKeyword =
        !kw ||
        item.fullName.toLowerCase().includes(kw) ||
        item.studentCode.toLowerCase().includes(kw) ||
        item.majorClass.toLowerCase().includes(kw);

      const matchClass = cls === 'all' || item.classCode === cls;
      const matchCond = cond === 'all' || item.examCondition === cond;

      return matchKeyword && matchClass && matchCond;
    });
  });

  // Paginated students
  paginatedStudents = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredStudents().slice(start, start + this.pageSize());
  });

  onFilterChange(): void {
    this.currentPage.set(1);
  }

  setPage(page: number): void {
    this.currentPage.set(page);
  }

  openDetail(student: AdminStudentItem): void {
    this.selectedStudent.set(student);
    this.editCondition.set(student.examCondition);
    this.editConditionNote.set(student.examConditionNote || '');
    this.saveSuccessMessage.set('');
    this.activeView.set('detail');
  }

  backToList(): void {
    this.activeView.set('list');
    this.selectedStudent.set(null);
    this.saveSuccessMessage.set('');
  }

  saveConditionChanges(): void {
    const current = this.selectedStudent();
    if (!current) return;

    this.adminService.updateExamCondition(
      current.id,
      this.editCondition(),
      this.editConditionNote()
    );

    // Update local selected student
    this.selectedStudent.set({
      ...current,
      examCondition: this.editCondition(),
      examConditionNote: this.editConditionNote()
    });

    this.saveSuccessMessage.set('Đã cập nhật trạng thái điều kiện dự thi thành công!');
    setTimeout(() => {
      this.saveSuccessMessage.set('');
    }, 3000);
  }

  exportExcel(): void {
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      ['Mã SV,Họ tên,Lớp,Học phần,LiveClass,Luyện tập,TX/GK,Điều kiện dự thi']
        .concat(
          this.filteredStudents().map(
            (s) =>
              `${s.studentCode},"${s.fullName}",${s.majorClass},"${s.subjectName}",${s.liveClassCompleted}/${s.liveClassTotal},${s.practiceCompleted}/${s.practiceTotal},${s.testCompleted}/${s.testTotal},${s.examCondition}`
          )
        )
        .join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `danh_sach_sinh_vien_ren_luyen.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
