import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  SearchInputComponent,
  PaginationComponent,
  SelectComponent,
  SelectOption
} from '@shared/components';
import { AdminDataService } from '../services/admin-data.service';
import { AdminCourseClass } from '../models/admin.model';

@Component({
  selector: 'app-admin-courses',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SearchInputComponent,
    PaginationComponent,
    SelectComponent
  ],
  templateUrl: './admin-courses.component.html',
  styleUrl: './admin-courses.component.scss'
})
export class AdminCoursesComponent {
  protected readonly Math = Math;
  private adminService = inject(AdminDataService);

  searchKeyword = signal<string>('');
  statusFilter = signal<string>('all');

  statusOptions: SelectOption[] = [
    { label: 'Tất cả trạng thái', value: 'all' },
    { label: 'Đang diễn ra', value: 'ongoing' },
    { label: 'Đã hoàn thành', value: 'completed' },
    { label: 'Sắp diễn ra', value: 'upcoming' }
  ];

  currentPage = signal<number>(1);
  pageSize = signal<number>(5);

  filteredClasses = computed(() => {
    const kw = this.searchKeyword().toLowerCase().trim();
    const st = this.statusFilter();

    return this.adminService.classes().filter((c) => {
      const matchKeyword =
        !kw ||
        c.subjectName.toLowerCase().includes(kw) ||
        c.classCode.toLowerCase().includes(kw) ||
        c.teacher.toLowerCase().includes(kw);

      const matchStatus = st === 'all' || c.status === st;

      return matchKeyword && matchStatus;
    });
  });

  paginatedClasses = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredClasses().slice(start, start + this.pageSize());
  });

  onFilterChange(): void {
    this.currentPage.set(1);
  }

  setPage(page: number): void {
    this.currentPage.set(page);
  }
}
