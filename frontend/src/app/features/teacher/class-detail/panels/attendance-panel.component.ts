import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideX } from '@lucide/angular';
import { TeacherClassService } from '../../services/teacher-class.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AttendanceSession, AttendanceState, GradebookStudentItem } from '../../models/teacher.model';

interface Draft {
  id?: string;
  date: string; // yyyy-MM-dd
  title: string;
  records: { [userId: string]: AttendanceState };
}

const STATES: { value: AttendanceState; label: string }[] = [
  { value: 'present', label: 'Có mặt' },
  { value: 'late', label: 'Muộn' },
  { value: 'excused', label: 'Có phép' },
  { value: 'absent', label: 'Vắng' }
];

@Component({
  selector: 'app-attendance-panel',
  standalone: true,
  imports: [FormsModule, DatePipe, LucideX],
  styleUrl: './panel.scss',
  styles: [`
    .rule { font-size: 0.84rem; color: var(--text-muted); }
    .student-list { display: flex; flex-direction: column; }
    .student-row { display: flex; align-items: center; justify-content: space-between; gap: 12px;
      padding: 9px 0; border-bottom: 1px solid var(--border-color-light); }
    .student-row:last-child { border-bottom: none; }
    .student-name { font-size: 0.9rem; }
    .student-name small { color: var(--text-muted); margin-left: 6px; }
    @media (max-width: 640px) { .student-row { flex-direction: column; align-items: flex-start; } }
  `],
  template: `
    <div class="panel-toolbar">
      <span class="rule">Chuyên cần = trung bình các buổi × 10 · Có mặt 1 · Muộn / Có phép 0.5 · Vắng 0</span>
      @if (!locked) {
        <button type="button" class="btn btn-primary" (click)="newSession()">Thêm buổi điểm danh</button>
      }
    </div>

    @if (loading()) {
      <div class="empty">Đang tải...</div>
    } @else if (sessions().length === 0) {
      <div class="empty">Chưa có buổi điểm danh. Khi chưa điểm danh, chuyên cần dùng điểm giảng viên nhập tay.</div>
    } @else {
      <div class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr><th>Ngày</th><th>Buổi</th><th class="num">Có mặt</th><th class="num">Muộn</th>
              <th class="num">Có phép</th><th class="num">Vắng</th><th></th></tr>
          </thead>
          <tbody>
            @for (s of sessions(); track s.id) {
              <tr>
                <td>{{ s.date | date: 'dd/MM/yyyy' }}</td>
                <td class="muted">{{ s.title || '—' }}</td>
                <td class="num">{{ count(s, 'present') }}</td>
                <td class="num">{{ count(s, 'late') }}</td>
                <td class="num">{{ count(s, 'excused') }}</td>
                <td class="num">{{ count(s, 'absent') }}</td>
                <td>
                  <button type="button" class="link-btn" (click)="edit(s)">{{ locked ? 'Xem' : 'Sửa' }}</button>
                  @if (!locked) {
                    <button type="button" class="link-btn danger" (click)="remove(s)">Xóa</button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }

    @if (draft(); as d) {
      <div class="modal-backdrop" (click)="close()">
        <div class="modal-card" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <div class="modal-header">
            <h3>{{ d.id ? 'Buổi điểm danh' : 'Thêm buổi điểm danh' }}</h3>
            <button type="button" class="modal-close" (click)="close()" aria-label="Đóng"><svg lucideX [size]="20"></svg></button>
          </div>
          <div class="modal-body">
            <div class="form-grid">
              <div class="field">
                <label for="at-date">Ngày</label>
                <input id="at-date" type="date" [disabled]="locked" [(ngModel)]="d.date" />
              </div>
              <div class="field">
                <label for="at-title">Tên buổi</label>
                <input id="at-title" [disabled]="locked" [(ngModel)]="d.title" maxlength="120" placeholder="VD: Buổi 3" />
              </div>
            </div>

            @if (!locked) {
              <div class="panel-toolbar" style="margin: 16px 0 4px;">
                <strong>{{ students.length }} sinh viên</strong>
                <button type="button" class="link-btn" (click)="markAll('present')">Tất cả có mặt</button>
              </div>
            }
            <div class="student-list">
              @for (st of students; track st.user_id) {
                <div class="student-row">
                  <span class="student-name">{{ st.student_name }}<small>{{ st.student_code }}</small></span>
                  <div class="segmented" role="radiogroup" [attr.aria-label]="'Điểm danh ' + st.student_name">
                    @for (opt of states; track opt.value) {
                      <button type="button" role="radio" [class]="'state-' + opt.value"
                        [class.active]="d.records[st.user_id] === opt.value"
                        [attr.aria-checked]="d.records[st.user_id] === opt.value"
                        [disabled]="locked" (click)="d.records[st.user_id] = opt.value">{{ opt.label }}</button>
                    }
                  </div>
                </div>
              }
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" (click)="close()">{{ locked ? 'Đóng' : 'Hủy' }}</button>
            @if (!locked) {
              <button type="button" class="btn btn-primary" [disabled]="saving()" (click)="save()">
                {{ saving() ? 'Đang lưu...' : 'Lưu điểm danh' }}
              </button>
            }
          </div>
        </div>
      </div>
    }
  `
})
export class AttendancePanelComponent implements OnInit {
  @Input({ required: true }) courseId!: string;
  @Input({ required: true }) students: GradebookStudentItem[] = [];
  @Input() locked = false;
  @Output() changed = new EventEmitter<void>();

  private service = inject(TeacherClassService);
  private toast = inject(ToastService);

  readonly states = STATES;
  sessions = signal<AttendanceSession[]>([]);
  loading = signal(false);
  saving = signal(false);
  draft = signal<Draft | null>(null);

  ngOnInit(): void {
    this.reload();
  }

  private reload(): void {
    this.loading.set(true);
    this.service.loadAttendance(this.courseId).subscribe({
      next: (list) => {
        this.sessions.set(list);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toast.error('Không tải được dữ liệu điểm danh.');
      }
    });
  }

  count(s: AttendanceSession, state: AttendanceState): number {
    return Object.values(s.records).filter((v) => v === state).length;
  }

  newSession(): void {
    const records: Draft['records'] = {};
    this.students.forEach((st) => (records[st.user_id] = 'present'));
    const today = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    this.draft.set({
      date: `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`,
      title: `Buổi ${this.sessions().length + 1}`,
      records
    });
  }

  edit(s: AttendanceSession): void {
    const d = new Date(s.date);
    const pad = (n: number) => String(n).padStart(2, '0');
    const records: Draft['records'] = {};
    // SV ghi danh sau buổi này chưa có bản ghi: mặc định có mặt khi GV mở để sửa
    this.students.forEach((st) => (records[st.user_id] = s.records[st.user_id] || 'present'));
    this.draft.set({ id: s.id, date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`, title: s.title || '', records });
  }

  markAll(state: AttendanceState): void {
    const d = this.draft();
    if (!d) return;
    Object.keys(d.records).forEach((k) => (d.records[k] = state));
    this.draft.set({ ...d, records: { ...d.records } });
  }

  close(): void {
    if (!this.saving()) this.draft.set(null);
  }

  save(): void {
    const d = this.draft();
    if (!d || !d.date) {
      this.toast.warning('Vui lòng chọn ngày.');
      return;
    }
    this.saving.set(true);
    // Lưu 07:00 giờ địa phương để ngày không bị lệch khi đổi múi giờ
    const iso = new Date(`${d.date}T07:00:00`).toISOString();
    this.service.saveAttendance(this.courseId, { id: d.id, date: iso, title: d.title.trim(), records: d.records }).subscribe({
      next: () => {
        this.saving.set(false);
        this.draft.set(null);
        this.toast.success('Đã lưu điểm danh, chuyên cần được tính lại.');
        this.reload();
        this.changed.emit();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error(err?.error?.message || 'Không lưu được điểm danh.');
      }
    });
  }

  remove(s: AttendanceSession): void {
    if (!confirm(`Xóa buổi điểm danh ngày ${new Date(s.date).toLocaleDateString('vi-VN')}?`)) return;
    this.service.deleteAttendance(this.courseId, s.id).subscribe({
      next: () => {
        this.toast.success('Đã xóa buổi điểm danh.');
        this.reload();
        this.changed.emit();
      },
      error: (err) => this.toast.error(err?.error?.message || 'Không xóa được.')
    });
  }
}
