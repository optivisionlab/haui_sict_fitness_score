import { Component, EventEmitter, Input, OnChanges, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TeacherClassService } from '../../services/teacher-class.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ExamEligibility, GradingFormula } from '../../models/teacher.model';

@Component({
  selector: 'app-settings-panel',
  standalone: true,
  imports: [FormsModule],
  styleUrl: './panel.scss',
  styles: [`
    .section { padding: 18px 0; border-bottom: 1px solid var(--border-color-light); }
    .section:first-child { padding-top: 0; }
    .section h4 { margin: 0 0 12px; font-size: 1rem; }
    .formula { margin: 0 0 14px; padding: 10px 12px; border-radius: 8px; background: #f8fafc; font-size: 0.88rem; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; max-width: 640px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; max-width: 430px; margin-top: 12px; }
    .sum { margin-top: 10px; font-size: 0.85rem; }
    .sum.bad { color: #dc2626; }
    .actions { padding-top: 18px; display: flex; justify-content: flex-end; }
    @media (max-width: 640px) { .grid-3, .grid-2 { grid-template-columns: 1fr; } }
  `],
  template: `
    <div class="section">
      <h4>Tỷ trọng điểm</h4>
      <p class="formula">
        Tổng kết = Chuyên cần × {{ att }} + Quá trình × {{ prc }} + Thi × {{ exm }}
        <br /><span class="muted">Quá trình = trung bình các bài thường xuyên và thi giữa kỳ · Thi = thi kết thúc học phần</span>
      </p>
      <div class="grid-3">
        <div class="field">
          <label for="st-att">Chuyên cần</label>
          <input id="st-att" type="number" min="0" max="1" step="0.05" [disabled]="locked" [(ngModel)]="att" />
        </div>
        <div class="field">
          <label for="st-prc">Quá trình</label>
          <input id="st-prc" type="number" min="0" max="1" step="0.05" [disabled]="locked" [(ngModel)]="prc" />
        </div>
        <div class="field">
          <label for="st-exm">Thi</label>
          <input id="st-exm" type="number" min="0" max="1" step="0.05" [disabled]="locked" [(ngModel)]="exm" />
        </div>
      </div>
      <div class="sum" [class.bad]="!sumOk()">Tổng: {{ sum() }} {{ sumOk() ? '' : '(phải bằng 1)' }}</div>
    </div>

    <div class="section">
      <h4>Điều kiện dự thi kết thúc học phần</h4>
      <label class="check-row">
        <input type="checkbox" [disabled]="locked" [(ngModel)]="eligEnabled" />
        <span>Áp dụng điều kiện dự thi</span>
      </label>
      @if (eligEnabled) {
        <div class="grid-2">
          <div class="field">
            <label for="st-min-att">Chuyên cần tối thiểu</label>
            <input id="st-min-att" type="number" min="0" max="10" step="0.5" [disabled]="locked" [(ngModel)]="minAtt" />
          </div>
          <div class="field">
            <label for="st-min-prc">Điểm quá trình tối thiểu</label>
            <input id="st-min-prc" type="number" min="0" max="10" step="0.5" [disabled]="locked" [(ngModel)]="minPrc" />
          </div>
        </div>
        <p class="muted" style="margin-top: 10px; font-size: 0.84rem;">
          Sinh viên không đạt sẽ không nộp được bài thi kết thúc và nhận điểm F.
        </p>
      }
    </div>

    @if (!locked) {
      <div class="actions">
        <button type="button" class="btn btn-primary" [disabled]="saving() || !sumOk()" (click)="save()">
          {{ saving() ? 'Đang lưu...' : 'Lưu và tính lại điểm' }}
        </button>
      </div>
    }
  `
})
export class SettingsPanelComponent implements OnChanges {
  @Input({ required: true }) courseId!: string;
  @Input({ required: true }) formula!: GradingFormula;
  @Input({ required: true }) eligibility!: ExamEligibility;
  @Input() locked = false;
  @Output() changed = new EventEmitter<void>();

  private service = inject(TeacherClassService);
  private toast = inject(ToastService);

  att = 0.1;
  prc = 0.3;
  exm = 0.6;
  eligEnabled = true;
  minAtt = 5;
  minPrc = 4;
  saving = signal(false);

  ngOnChanges(): void {
    this.att = this.formula?.attendance_weight ?? 0.1;
    this.prc = this.formula?.process_weight ?? 0.3;
    this.exm = this.formula?.exam_weight ?? 0.6;
    this.eligEnabled = this.eligibility?.enabled ?? true;
    this.minAtt = this.eligibility?.min_attendance_score ?? 5;
    this.minPrc = this.eligibility?.min_process_score ?? 4;
  }

  sum(): number {
    return Math.round((Number(this.att) + Number(this.prc) + Number(this.exm)) * 1000) / 1000;
  }

  sumOk(): boolean {
    return Math.abs(this.sum() - 1) < 1e-6;
  }

  save(): void {
    this.saving.set(true);
    this.service.saveGradingSettings(
      this.courseId,
      { attendance_weight: Number(this.att), process_weight: Number(this.prc), exam_weight: Number(this.exm) },
      { enabled: this.eligEnabled, min_attendance_score: Number(this.minAtt), min_process_score: Number(this.minPrc) }
    ).subscribe({
      next: () => {
        this.saving.set(false);
        this.toast.success('Đã lưu cấu hình và tính lại điểm cả lớp.');
        this.changed.emit();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error(err?.error?.message || 'Không lưu được cấu hình.');
      }
    });
  }
}
