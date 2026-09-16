import { Component, computed, input, model, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideChevronLeft,
  LucideChevronRight,
  LucideChevronsLeft,
  LucideChevronsRight
} from '@lucide/angular';

export type PageItem = number | '...';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [
    CommonModule,
    LucideChevronLeft,
    LucideChevronRight,
    LucideChevronsLeft,
    LucideChevronsRight
  ],
  templateUrl: './pagination.component.html',
  styleUrl: './pagination.component.scss'
})
export class PaginationComponent {
  /** Current active page (1-based index) */
  currentPage = model<number>(1);

  /** Total number of items across all pages */
  totalItems = input<number>(0);

  /** Items per page */
  pageSize = input<number>(10);

  /** Whether to show the item count summary info */
  showInfo = input<boolean>(true);

  /** Emits when page changes */
  pageChange = output<number>();

  /** Total pages calculated from total items and page size */
  totalPages = computed(() => {
    const size = Math.max(1, this.pageSize());
    return Math.max(1, Math.ceil(this.totalItems() / size));
  });

  /** First item index in current page (1-based) */
  startItem = computed(() => {
    if (this.totalItems() === 0) return 0;
    return (this.currentPage() - 1) * this.pageSize() + 1;
  });

  /** Last item index in current page */
  endItem = computed(() => {
    return Math.min(this.currentPage() * this.pageSize(), this.totalItems());
  });

  /** Visible pages with optional ellipsis */
  pages = computed<PageItem[]>(() => {
    const total = this.totalPages();
    const current = this.currentPage();

    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }

    if (current <= 4) {
      return [1, 2, 3, 4, 5, '...', total];
    }

    if (current >= total - 3) {
      return [1, '...', total - 4, total - 3, total - 2, total - 1, total];
    }

    return [1, '...', current - 1, current, current + 1, '...', total];
  });

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages() && page !== this.currentPage()) {
      this.currentPage.set(page);
      this.pageChange.emit(page);
    }
  }

  prevPage(): void {
    if (this.currentPage() > 1) {
      this.goToPage(this.currentPage() - 1);
    }
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.goToPage(this.currentPage() + 1);
    }
  }

  firstPage(): void {
    if (this.currentPage() > 1) {
      this.goToPage(1);
    }
  }

  lastPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.goToPage(this.totalPages());
    }
  }
}
