import { Component, ElementRef, OnDestroy, ViewChild, effect, input, output, signal } from '@angular/core';

/** Thứ tự 4 góc nửa sân đối phương, khớp với dịch vụ AI (mode MATCH). */
const CORNER_LABELS = [
  'Đầu lưới bên TRÁI (chỗ lưới gặp đường biên dọc)',
  'Đầu lưới bên PHẢI',
  'Góc cuối sân bên PHẢI (phía đối phương)',
  'Góc cuối sân bên TRÁI (phía đối phương)'
];

/**
 * Bài quay đối kháng: sinh viên bấm 4 góc nửa sân đối phương trên khung hình đầu của video
 * (công thức 24 của đề án). Phát ra 4 điểm [x, y] chuẩn hóa về [0, 1], hoặc null khi chưa đủ.
 * Khung hình được lấy ngay trong trình duyệt, không cần tải video lên trước.
 */
@Component({
  selector: 'app-court-marker',
  standalone: true,
  template: `
    <div class="court-marker">
      <div class="cm-head">
        <strong>Đánh dấu sân (không bắt buộc)</strong>
        @if (points().length) {
          <button type="button" class="cm-reset" (click)="reset()">Đánh dấu lại</button>
        }
      </div>
      @if (error()) {
        <p class="cm-hint cm-warn">{{ error() }}</p>
      } @else {
        <p class="cm-hint">
          @if (points().length < 4) {
            Bấm điểm {{ points().length + 1 }}/4: <strong>{{ labels[points().length] }}</strong>
          } @else {
            Đã đánh dấu đủ 4 góc. AI sẽ kiểm tra bóng nảy trong vùng đích{{ zoneLabel() ? ': ' + zoneLabel() : '' }}.
          }
        </p>
      }
      <canvas #canvas class="cm-canvas" [class.hidden]="!ready()" (click)="onClick($event)"></canvas>
      @if (!ready() && !error()) {
        <div class="cm-loading">Đang lấy khung hình đầu của video...</div>
      }
      <p class="cm-note">
        Bỏ qua bước này thì AI tự ước lượng vị trí lưới và không kiểm tra vùng đích.
      </p>
    </div>
  `,
  styles: [`
    .court-marker { margin-top: 12px; padding: 12px; border: 1px dashed #93c5fd; border-radius: 10px; background: #f8fbff; }
    .cm-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .cm-reset { border: none; background: none; color: #2563eb; cursor: pointer; font-size: 0.85rem; }
    .cm-hint { margin: 6px 0; font-size: 0.88rem; }
    .cm-warn { color: #b45309; }
    .cm-note { margin: 6px 0 0; font-size: 0.78rem; color: #64748b; }
    .cm-canvas { width: 100%; max-height: 50vh; object-fit: contain; border-radius: 6px; cursor: crosshair; display: block; }
    .cm-loading { padding: 24px; text-align: center; font-size: 0.85rem; color: #64748b; }
    .hidden { display: none; }
  `]
})
export class CourtMarkerComponent implements OnDestroy {
  file = input<File | null>(null);
  zoneLabel = input<string>('');
  pointsChange = output<number[][] | null>();

  @ViewChild('canvas', { static: true }) private canvasRef!: ElementRef<HTMLCanvasElement>;

  readonly labels = CORNER_LABELS;
  points = signal<number[][]>([]);
  ready = signal(false);
  error = signal('');

  private frame: HTMLCanvasElement | null = null;
  private objectUrl: string | null = null;
  private video: HTMLVideoElement | null = null;

  constructor() {
    effect(() => this.load(this.file()));
  }

  ngOnDestroy(): void {
    this.release();
  }

  reset(): void {
    this.points.set([]);
    this.pointsChange.emit(null);
    this.draw();
  }

  onClick(event: MouseEvent): void {
    if (!this.ready() || this.points().length >= 4) return;
    const canvas = this.canvasRef.nativeElement;
    const rect = canvas.getBoundingClientRect();
    // object-fit: contain giữ tỉ lệ: tính vùng ảnh thật trong khung hiển thị
    const scale = Math.min(rect.width / canvas.width, rect.height / canvas.height);
    const w = canvas.width * scale;
    const h = canvas.height * scale;
    const x = (event.clientX - rect.left - (rect.width - w) / 2) / w;
    const y = (event.clientY - rect.top - (rect.height - h) / 2) / h;
    if (x < 0 || x > 1 || y < 0 || y > 1) return;
    const next = [...this.points(), [Math.round(x * 10000) / 10000, Math.round(y * 10000) / 10000]];
    this.points.set(next);
    this.draw();
    this.pointsChange.emit(next.length === 4 ? next : null);
  }

  private load(file: File | null): void {
    this.release();
    this.points.set([]);
    this.ready.set(false);
    this.error.set('');
    this.pointsChange.emit(null);
    if (!file) return;

    const video = document.createElement('video');
    video.muted = true;
    video.playsInline = true;
    video.preload = 'auto';
    this.video = video;
    this.objectUrl = URL.createObjectURL(file);
    video.onloadeddata = () => {
      video.currentTime = Math.min(0.1, (video.duration || 1) / 2);
    };
    video.onseeked = () => {
      if (this.video !== video) return;
      const frame = document.createElement('canvas');
      frame.width = video.videoWidth;
      frame.height = video.videoHeight;
      frame.getContext('2d')?.drawImage(video, 0, 0);
      this.frame = frame;
      const canvas = this.canvasRef.nativeElement;
      canvas.width = frame.width;
      canvas.height = frame.height;
      this.ready.set(true);
      this.draw();
    };
    video.onerror = () => {
      if (this.video !== video) return;
      this.error.set('Trình duyệt không đọc được video này để đánh dấu sân. Bạn vẫn nộp được, AI sẽ tự ước lượng lưới.');
    };
    video.src = this.objectUrl;
  }

  private draw(): void {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx || !this.frame) return;
    ctx.drawImage(this.frame, 0, 0);
    const pts = this.points().map(([x, y]) => [x * canvas.width, y * canvas.height]);
    const r = Math.max(6, canvas.width / 160);
    ctx.lineWidth = Math.max(2, canvas.width / 480);
    if (pts.length >= 2) {
      // Cạnh 1-2 là lưới (đỏ), các cạnh còn lại là biên nửa sân đối phương (vàng)
      ctx.strokeStyle = '#ef4444';
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      ctx.lineTo(pts[1][0], pts[1][1]);
      ctx.stroke();
      ctx.strokeStyle = '#facc15';
      ctx.beginPath();
      ctx.moveTo(pts[1][0], pts[1][1]);
      for (const p of pts.slice(2)) ctx.lineTo(p[0], p[1]);
      if (pts.length === 4) ctx.lineTo(pts[0][0], pts[0][1]);
      ctx.stroke();
    }
    ctx.font = `bold ${Math.round(r * 2)}px sans-serif`;
    pts.forEach(([x, y], i) => {
      ctx.fillStyle = '#2563eb';
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.fillText(String(i + 1), x + r * 1.2, y - r * 1.2);
    });
  }

  private release(): void {
    if (this.video) {
      this.video.removeAttribute('src');
      this.video.load();
      this.video = null;
    }
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = null;
    }
    this.frame = null;
  }
}
