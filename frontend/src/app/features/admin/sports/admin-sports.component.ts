import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideTrophy,
  LucidePlus,
  LucideSearch,
  LucideEdit3,
  LucideTrash2,
  LucideVideo,
  LucideActivity,
  LucideCheckCircle2,
  LucideAlertCircle,
  LucideX
} from '@lucide/angular';
import { AdminService, Sport, SportCreateRequest } from '@core/services/admin.service';
import { ToastService } from '@core/services/toast.service';

@Component({
  selector: 'app-admin-sports',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideTrophy,
    LucidePlus,
    LucideSearch,
    LucideEdit3,
    LucideTrash2,
    LucideVideo,
    LucideActivity,
    LucideCheckCircle2,
    LucideAlertCircle,
    LucideX
  ],
  templateUrl: './admin-sports.component.html',
  styleUrl: './admin-sports.component.scss'
})
export class AdminSportsComponent implements OnInit {
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);

  sports = signal<Sport[]>([]);
  isLoading = signal<boolean>(true);
  searchTerm = signal<string>('');

  // Modal State
  showModal = signal<boolean>(false);
  isEditMode = signal<boolean>(false);
  isSubmitting = signal<boolean>(false);

  // Form State
  currentSportId = signal<string | null>(null);
  formData: SportCreateRequest = {
    code: '',
    name: '',
    mode: 'video',
    scoring_config: {
      metrics_fields: ['accuracy', 'form_score'],
      formula: null,
      thresholds: {}
    }
  };
  metricsInput = signal<string>('accuracy, form_score');

  // Delete Confirm State
  showDeleteModal = signal<boolean>(false);
  sportToDelete = signal<Sport | null>(null);

  ngOnInit(): void {
    this.loadSports();
  }

  loadSports(): void {
    this.isLoading.set(true);
    this.adminService.getSports(1, 100).subscribe({
      next: (res) => {
        this.sports.set(res.items || []);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.toastService.error('Không thể tải danh sách môn học: ' + (err.message || 'Lỗi server'));
      }
    });
  }

  get filteredSports(): Sport[] {
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return this.sports();
    return this.sports().filter(s =>
      s.name.toLowerCase().includes(term) || s.code.toLowerCase().includes(term)
    );
  }

  openCreateModal(): void {
    this.isEditMode.set(false);
    this.currentSportId.set(null);
    this.formData = {
      code: '',
      name: '',
      mode: 'video',
      scoring_config: {
        metrics_fields: ['accuracy', 'form_score'],
        formula: null,
        thresholds: {}
      }
    };
    this.metricsInput.set('accuracy, form_score');
    this.showModal.set(true);
  }

  openEditModal(sport: Sport): void {
    this.isEditMode.set(true);
    this.currentSportId.set(sport.id);
    const metrics = sport.scoring_config?.metrics_fields?.join(', ') || '';
    this.formData = {
      code: sport.code,
      name: sport.name,
      mode: sport.mode,
      scoring_config: {
        metrics_fields: sport.scoring_config?.metrics_fields || [],
        formula: sport.scoring_config?.formula || null,
        thresholds: sport.scoring_config?.thresholds || {}
      }
    };
    this.metricsInput.set(metrics);
    this.showModal.set(true);
  }

  closeModal(): void {
    this.showModal.set(false);
  }

  onSubmitSport(): void {
    if (!this.formData.code.trim() || !this.formData.name.trim()) {
      this.toastService.warning('Vui lòng nhập đầy đủ Mã môn và Tên môn học');
      return;
    }

    // Parse metrics
    const metricsArr = this.metricsInput()
      .split(',')
      .map(m => m.trim())
      .filter(m => m.length > 0);

    const payload: SportCreateRequest = {
      code: this.formData.code.trim().toUpperCase(),
      name: this.formData.name.trim(),
      mode: this.formData.mode,
      scoring_config: {
        metrics_fields: metricsArr,
        formula: null,
        thresholds: {}
      }
    };

    this.isSubmitting.set(true);

    if (this.isEditMode() && this.currentSportId()) {
      this.adminService.updateSport(this.currentSportId()!, payload).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`Cập nhật môn ${payload.name} thành công!`);
          this.closeModal();
          this.loadSports();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.toastService.error('Cập nhật thất bại: ' + (err.message || 'Lỗi server'));
        }
      });
    } else {
      this.adminService.createSport(payload).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`Thêm mới môn ${payload.name} thành công!`);
          this.closeModal();
          this.loadSports();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.toastService.error('Thêm mới thất bại: ' + (err.message || 'Lỗi server'));
        }
      });
    }
  }

  confirmDelete(sport: Sport): void {
    this.sportToDelete.set(sport);
    this.showDeleteModal.set(true);
  }

  cancelDelete(): void {
    this.showDeleteModal.set(false);
    this.sportToDelete.set(null);
  }

  onExecuteDelete(): void {
    const sport = this.sportToDelete();
    if (!sport) return;

    this.adminService.deleteSport(sport.id).subscribe({
      next: () => {
        this.toastService.success(`Đã xóa môn ${sport.name} thành công`);
        this.cancelDelete();
        this.loadSports();
      },
      error: (err) => {
        this.toastService.error('Không thể xóa môn học: ' + (err.message || 'Có lớp học phần đang dùng môn này'));
      }
    });
  }
}
