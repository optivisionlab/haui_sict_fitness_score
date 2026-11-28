import {
  Component, ElementRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild, computed, inject, signal
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideX } from '@lucide/angular';
import { TeacherClassService } from '../../services/teacher-class.service';
import { VideoResultService } from '../../../../core/services/video-result.service';
import { ToastService } from '../../../../core/services/toast.service';
import { GradebookTaskItem, TeacherSubmission } from '../../models/teacher.model';
import { metricChips, shotEvents } from '../../../../core/utils/match-metrics';

type ReviewFilter = 'pending' | 'latest' | 'all';

@Component({
  selector: 'app-review-panel',
  standalone: true,
  imports: [FormsModule, DatePipe, LucideX],
  styleUrl: './panel.scss',
  styles: [`
    .review-layout { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 20px; }
    .video-box { min-height: 260px; display: flex; align-items: center; justify-content: center;
      border-radius: 10px; background: #0f172a; color: #cbd5e1; overflow: hidden; }
    .video-box video { width: 100%; max-height: 60vh; display: block; }
    .facts { display: flex; flex-direction: column; gap: 12px; }
    .fact-row { display: flex; justify-content: space-between; gap: 12px; font-size: 0.9rem; }
    .ai-score { font-size: 1.6rem; font-weight: 700; color: var(--accent-blue); }
    .ai-comment { padding: 10px 12px; border-radius: 8px; background: #f8fafc; font-size: 0.88rem; line-height: 1.5; }
    .metrics { display: flex; flex-wrap: wrap; gap: 6px; }
    .shots { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; font-size: 0.85rem; }
    .shot { display: grid; grid-template-columns: 56px 52px 1fr; gap: 6px; align-items: center; text-align: left;
      padding: 4px 8px; border: 1px solid #fecaca; border-radius: 6px; background: #fef2f2; cursor: pointer; }
    .shot.hit { border-color: #bbf7d0; background: #f0fdf4; }
    .shot-time { font-variant-numeric: tabular-nums; font-weight: 600; }
    .score-input { max-width: 140px; }
    @media (max-width: 860px) { .review-layout { grid-template-columns: 1fr; } }
  `],
  template: `
    <div class="panel-toolbar">
      <div class="chip-row" role="tablist" aria-label="Chọn bài">
        @for (t of tasks; track t.id) {
          <button type="button" class="chip" role="tab" [class.active]="t.id === taskId()" (click)="selectTask(t.id)">
            {{ t.title }}
            @if (t.pending_review_count) { <span class="count">{{ t.pending_review_count }}</span> }
          </button>
        }
      </div>
      <div class="segmented" role="group" aria-label="Lọc bài nộp">
        <button type="button" [class.active]="filter() === 'pending'" (click)="filter.set('pending')">Chờ duyệt</button>
        <button type="button" [class.active]="filter() === 'latest'" (click)="filter.set('latest')">Lần mới nhất</button>
        <button type="button" [class.active]="filter() === 'all'" (click)="filter.set('all')">Tất cả</button>
      </div>
    </div>

    @if (loading()) {
      <div class="empty">Đang tải bài nộp...</div>
    } @else if (visible().length === 0) {
      <div class="empty">{{ filter() === 'pending' ? 'Không còn bài nào chờ duyệt.' : 'Chưa có bài nộp.' }}</div>
    } @else {
      <div class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mã SV</th><th>Họ tên</th><th class="num">Lần</th><th>Nộp lúc</th>
              <th class="num">Điểm AI</th><th class="num">Điểm GV</th><th>Trạng thái</th><th></th>
            </tr>
          </thead>
          <tbody>
            @for (s of visible(); track s.id) {
              <tr>
                <td>{{ s.student_code }}</td>
                <td>{{ s.student_name }}</td>
                <td class="num">{{ s.attempt_no }}</td>
                <td class="muted">{{ s.submitted_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                <td class="num">{{ s.ai_score ?? '—' }}</td>
                <td class="num"><strong>{{ s.final_score ?? '—' }}</strong></td>
                <td>
                  @if (s.final_score !== undefined) { <span class="pill ok">GV đã xác nhận</span> }
                  @else if (s.status === 'completed') { <span class="pill wait">Chờ duyệt</span> }
                  @else if (s.status === 'failed') { <span class="pill bad">AI lỗi</span> }
                  @else { <span class="pill">AI đang chấm</span> }
                </td>
                <td><button type="button" class="link-btn" (click)="open(s)">Xem & chấm</button></td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }

    @if (current(); as s) {
      <div class="modal-backdrop" (click)="closeReview()">
        <div class="modal-card wide" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <div class="modal-header">
            <div>
              <h3>{{ s.student_name }} · {{ s.student_code }}</h3>
              <p>{{ taskTitle() }} · Lần {{ s.attempt_no }} · {{ s.submitted_at | date: 'dd/MM/yyyy HH:mm' }}</p>
            </div>
            <button type="button" class="modal-close" (click)="closeReview()" aria-label="Đóng"><svg lucideX [size]="20"></svg></button>
          </div>

          <div class="modal-body">
            <div class="review-layout">
              <div class="video-box">
                @if (videoUrl()) {
                  <video #reviewVideo [src]="videoUrl()" controls playsinline preload="metadata"></video>
                } @else {
                  <span>{{ videoError() || 'Đang tải video...' }}</span>
                }
              </div>

              <div class="facts">
                <div class="fact-row">
                  <span class="muted">Điểm AI</span>
                  <span class="ai-score">{{ s.ai_score ?? '—' }}</span>
                </div>
                @if (s.ai_comment) { <div class="ai-comment">{{ s.ai_comment }}</div> }
                @if (metricChips(s.metrics).length) {
                  <div class="metrics">
                    @for (m of metricChips(s.metrics); track m.key) { <span class="pill info">{{ m.label }}: {{ m.value }}</span> }
                  </div>
                }
                @if (shotEvents(s.metrics).length) {
                  <div class="shots">
                    <span class="muted">Các cú đánh (bấm để tua video)</span>
                    @for (e of shotEvents(s.metrics); track $index) {
                      <button type="button" class="shot" [class.hit]="e.hit" (click)="seek(e.time)">
                        <span class="shot-time">{{ e.timeText }}</span>
                        <span>{{ e.hit ? 'Trúng' : 'Trượt' }}</span>
                        <span class="muted">{{ e.reason }}</span>
                      </button>
                    }
                  </div>
                }

                <div class="field">
                  <label for="rv-score">Điểm giảng viên (0–10)</label>
                  <input id="rv-score" class="score-input" type="number" min="0" max="10" step="0.1"
                    [disabled]="locked" [(ngModel)]="score" />
                </div>
                <div class="field">
                  <label for="rv-comment">Nhận xét gửi sinh viên</label>
                  <textarea id="rv-comment" rows="3" [disabled]="locked" [(ngModel)]="comment"></textarea>
                </div>
                @if (error()) { <div class="form-error" role="alert">{{ error() }}</div> }
              </div>
            </div>
          </div>

          <div class="modal-footer">
            @if (!locked && s.ai_score !== undefined) {
              <button type="button" class="btn btn-secondary" [disabled]="saving()" (click)="acceptAi()">Giữ điểm AI</button>
            }
            <span class="spacer"></span>
            <button type="button" class="btn btn-secondary" (click)="closeReview()">Đóng</button>
            @if (!locked) {
              <button type="button" class="btn btn-primary" [disabled]="saving()" (click)="save(true)">Lưu & bài tiếp</button>
            }
          </div>
        </div>
      </div>
    }
  `
})
export class ReviewPanelComponent implements OnChanges {
  @Input({ required: true }) courseId!: string;
  @Input({ required: true }) tasks: GradebookTaskItem[] = [];
  @Input() locked = false;
  @Input() initialTaskId: string | null = null;
  @Output() changed = new EventEmitter<void>();

  private service = inject(TeacherClassService);
  private videoService = inject(VideoResultService);
  private toast = inject(ToastService);

  taskId = signal<string>('');
  filter = signal<ReviewFilter>('pending');
  loading = signal(false);
  submissions = signal<TeacherSubmission[]>([]);

  current = signal<TeacherSubmission | null>(null);
  videoUrl = signal<string>('');
  videoError = signal<string>('');
  saving = signal(false);
  error = signal('');
  score: number | null = null;
  comment = '';

  taskTitle = computed(() => this.tasks.find((t) => t.id === this.taskId())?.title || '');

  visible = computed(() => {
    const list = this.submissions();
    if (this.filter() === 'all') return list;
    // Danh sách đã sắp xếp mới nhất trước: lần đầu gặp SV là lần nộp mới nhất
    const seen = new Set<string>();
    const latest = list.filter((s) => (seen.has(s.user_id) ? false : (seen.add(s.user_id), true)));
    return this.filter() === 'latest'
      ? latest
      : latest.filter((s) => s.status === 'completed' && s.final_score === undefined);
  });

  ngOnChanges(changes: SimpleChanges): void {
    const wanted = this.initialTaskId || this.taskId()
      || this.tasks.find((t) => t.pending_review_count)?.id || this.tasks[0]?.id || '';
    if (changes['initialTaskId'] || !this.taskId()) {
      if (wanted && wanted !== this.taskId()) this.selectTask(wanted);
    }
  }

  selectTask(id: string): void {
    this.taskId.set(id);
    this.reload();
  }

  private reload(): void {
    const id = this.taskId();
    if (!id) return;
    this.loading.set(true);
    this.service.loadSubmissions(this.courseId, id).subscribe({
      next: (list) => {
        this.submissions.set(list);
        this.loading.set(false);
      },
      error: () => {
        this.submissions.set([]);
        this.loading.set(false);
        this.toast.error('Không tải được danh sách bài nộp.');
      }
    });
  }

  readonly metricChips = metricChips;
  readonly shotEvents = shotEvents;
  @ViewChild('reviewVideo') private reviewVideo?: ElementRef<HTMLVideoElement>;

  /** Tua video tới cú đánh (giảng viên kiểm tra lại kết quả AI). */
  seek(time: number): void {
    const video = this.reviewVideo?.nativeElement;
    if (!video) return;
    video.currentTime = Math.max(0, time - 1);
    void video.play().catch(() => undefined);
  }

  open(s: TeacherSubmission): void {
    this.current.set(s);
    this.score = s.final_score ?? s.ai_score ?? null;
    this.comment = s.teacher_comment ?? '';
    this.error.set('');
    this.videoUrl.set('');
    this.videoError.set('');
    this.videoService.getVideoStreamUrl(s.id).subscribe({
      next: (res) => res?.data?.videoUrl ? this.videoUrl.set(res.data.videoUrl) : this.videoError.set('Bài nộp không có video.'),
      error: () => this.videoError.set('Không tải được video.')
    });
  }

  closeReview(): void {
    if (!this.saving()) this.current.set(null);
  }

  acceptAi(): void {
    const s = this.current();
    if (!s || s.ai_score === undefined) return;
    this.score = s.ai_score;
    this.save(true);
  }

  save(goNext: boolean): void {
    const s = this.current();
    const score = this.score === null || (this.score as unknown) === '' ? NaN : Number(this.score);
    if (!s) return;
    if (isNaN(score) || score < 0 || score > 10) {
      this.error.set('Điểm phải từ 0 đến 10.');
      return;
    }
    this.saving.set(true);
    this.error.set('');
    this.service.gradeSubmission(this.courseId, s.id, score, this.comment.trim()).subscribe({
      next: () => {
        this.saving.set(false);
        const updated = { ...s, final_score: score, teacher_comment: this.comment.trim() || undefined };
        this.submissions.update((list) => list.map((x) => (x.id === s.id ? updated : x)));
        this.changed.emit();
        const queue = this.visible();
        const next = goNext ? queue.find((x) => x.id !== s.id && x.status === 'completed' && x.final_score === undefined) : null;
        if (next) this.open(next); else this.current.set(null);
        this.toast.success(`Đã lưu điểm ${score} cho ${s.student_name}.`);
      },
      error: (err) => {
        this.saving.set(false);
        this.error.set(err?.error?.message || 'Không lưu được điểm.');
      }
    });
  }
}
