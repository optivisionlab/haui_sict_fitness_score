import { Component, EventEmitter, Input, OnChanges, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideX } from '@lucide/angular';
import { TeacherClassService } from '../../services/teacher-class.service';
import { ToastService } from '../../../../core/services/toast.service';
import { GradebookTaskItem, GradingMethod, TaskKind, TaskUpsert } from '../../models/teacher.model';

/** Chuyển ISO <-> giá trị của input datetime-local (giờ địa phương). */
function toLocalInput(iso?: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInput(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

@Component({
  selector: 'app-task-form',
  standalone: true,
  imports: [FormsModule, LucideX],
  styleUrl: './panel.scss',
  template: `
    <div class="modal-backdrop" (click)="close()">
      <div class="modal-card" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>{{ task ? 'Sửa bài kiểm tra' : 'Thêm bài kiểm tra' }}</h3>
          <button type="button" class="modal-close" (click)="close()" aria-label="Đóng"><svg lucideX [size]="20"></svg></button>
        </div>

        <div class="modal-body">
          <div class="form-grid">
            <div class="field full">
              <label for="tf-title">Tên bài</label>
              <input id="tf-title" [(ngModel)]="title" maxlength="200" placeholder="VD: TX3: Kỹ thuật phát bóng" />
            </div>

            <div class="field">
              <label for="tf-kind">Loại bài</label>
              <select id="tf-kind" [(ngModel)]="kind" (ngModelChange)="onKindChange($event)">
                <option value="regular">Kiểm tra thường xuyên</option>
                <option value="midterm">Thi giữa kỳ</option>
                <option value="final">Thi kết thúc học phần</option>
              </select>
              <span class="hint">{{ kind === 'final' ? 'Điểm thi' : 'Tính vào điểm quá trình' }}</span>
            </div>

            <div class="field">
              <label for="tf-method">Cách lấy điểm khi nộp nhiều lần</label>
              <select id="tf-method" [(ngModel)]="gradingMethod">
                <option value="highest">Lần cao nhất</option>
                <option value="latest">Lần nộp gần nhất</option>
                <option value="average">Trung bình các lần</option>
              </select>
            </div>

            <div class="field">
              <label for="tf-open">Thời gian mở</label>
              <input id="tf-open" type="datetime-local" [(ngModel)]="openTime" />
            </div>

            <div class="field">
              <label for="tf-close">Hạn nộp</label>
              <input id="tf-close" type="datetime-local" [(ngModel)]="closeTime" />
            </div>

            <div class="field">
              <label for="tf-limit">Thời lượng video tối đa (giây)</label>
              <input id="tf-limit" type="number" min="1" max="3600" [(ngModel)]="timeLimit" placeholder="Không giới hạn" />
            </div>

            <div class="field" style="justify-content: flex-end;">
              <label class="check-row">
                <input type="checkbox" [(ngModel)]="isLocked" />
                <span>Khóa nộp bài</span>
              </label>
            </div>

            <div class="field full">
              <label for="tf-desc">Yêu cầu kỹ thuật</label>
              <textarea id="tf-desc" [(ngModel)]="description" maxlength="2000" rows="3"></textarea>
            </div>
          </div>

          @if (error()) {
            <div class="form-error" role="alert">{{ error() }}</div>
          }
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" (click)="close()">Hủy</button>
          <button type="button" class="btn btn-primary" [disabled]="saving()" (click)="save()">
            {{ saving() ? 'Đang lưu...' : (task ? 'Lưu thay đổi' : 'Thêm bài') }}
          </button>
        </div>
      </div>
    </div>
  `
})
export class TaskFormComponent implements OnChanges {
  @Input({ required: true }) courseId!: string;
  /** null = tạo bài mới. */
  @Input() task: GradebookTaskItem | null = null;
  @Output() saved = new EventEmitter<void>();
  @Output() closed = new EventEmitter<void>();

  private service = inject(TeacherClassService);
  private toast = inject(ToastService);

  title = '';
  kind: TaskKind = 'regular';
  gradingMethod: GradingMethod = 'highest';
  description = '';
  openTime = '';
  closeTime = '';
  timeLimit: number | null = null;
  isLocked = false;

  saving = signal(false);
  error = signal('');

  ngOnChanges(): void {
    const t = this.task;
    this.title = t?.title ?? '';
    this.kind = t?.kind ?? 'regular';
    this.gradingMethod = t?.grading_method ?? 'highest';
    this.description = t?.description ?? '';
    this.openTime = toLocalInput(t?.open_time);
    this.closeTime = toLocalInput(t?.close_time);
    this.timeLimit = t?.time_limit ?? null;
    this.isLocked = t?.is_locked ?? false;
    this.error.set('');
  }

  /** Bài thi mặc định lấy lần nộp gần nhất, bài thường xuyên lấy lần cao nhất. */
  onKindChange(kind: TaskKind): void {
    if (!this.task) this.gradingMethod = kind === 'regular' ? 'highest' : 'latest';
  }

  close(): void {
    if (!this.saving()) this.closed.emit();
  }

  save(): void {
    const title = this.title.trim();
    if (!title) {
      this.error.set('Vui lòng nhập tên bài.');
      return;
    }
    if (this.openTime && this.closeTime && new Date(this.closeTime) <= new Date(this.openTime)) {
      this.error.set('Hạn nộp phải sau thời gian mở.');
      return;
    }
    const body: TaskUpsert = {
      title,
      kind: this.kind,
      description: this.description.trim() || null,
      grading_method: this.gradingMethod,
      time_limit: this.timeLimit ? Number(this.timeLimit) : null,
      open_time: fromLocalInput(this.openTime),
      close_time: fromLocalInput(this.closeTime),
      is_locked: this.isLocked
    };
    this.saving.set(true);
    this.error.set('');
    const req = this.task
      ? this.service.updateTask(this.courseId, this.task.id, body)
      : this.service.createTask(this.courseId, body);
    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.toast.success(this.task ? 'Đã lưu bài kiểm tra.' : 'Đã thêm bài kiểm tra.');
        this.saved.emit();
      },
      error: (err) => {
        this.saving.set(false);
        this.error.set(err?.error?.detail || err?.error?.message || 'Không lưu được bài kiểm tra.');
      }
    });
  }
}
