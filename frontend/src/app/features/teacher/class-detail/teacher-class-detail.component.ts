import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpEventType } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import {
  LucideArrowLeft,
  LucideLock,
  LucideUnlock,
  LucideCheckCircle2,
  LucideUsers,
  LucideAward,
  LucideFileSpreadsheet,
  LucideCheck,
  LucideX,
  LucideEdit3,
  LucideActivity,
  LucideShieldAlert,
  LucideVideo,
  LucideUploadCloud,
  LucideTrash2,
  LucideEye,
  LucideCalendarCheck,
  LucideSettings
} from '@lucide/angular';
import { Observable } from 'rxjs';
import { ReviewPanelComponent } from './panels/review-panel.component';
import { AttendancePanelComponent } from './panels/attendance-panel.component';
import { SettingsPanelComponent } from './panels/settings-panel.component';
import { TaskFormComponent } from './panels/task-form.component';
import {
  SearchInputComponent,
  SelectComponent,
  SelectOption
} from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import { VideoResultService } from '../../../core/services/video-result.service';
import { ToastService } from '../../../core/services/toast.service';
import { GradebookStudentItem, GradebookTaskItem, GradingMethod, TaskKind } from '../models/teacher.model';

type ClassTab = 'students' | 'assessments' | 'review' | 'attendance' | 'settings' | 'stats';

@Component({
  selector: 'app-teacher-class-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideArrowLeft,
    LucideLock,
    LucideUnlock,
    LucideCheckCircle2,
    LucideUsers,
    LucideAward,
    LucideFileSpreadsheet,
    LucideCheck,
    LucideX,
    LucideEdit3,
    LucideActivity,
    LucideShieldAlert,
    LucideVideo,
    LucideUploadCloud,
    LucideTrash2,
    LucideEye,
    LucideCalendarCheck,
    LucideSettings,
    ReviewPanelComponent,
    AttendancePanelComponent,
    SettingsPanelComponent,
    TaskFormComponent,
    SearchInputComponent,
    SelectComponent
  ],
  templateUrl: './teacher-class-detail.component.html',
  styleUrl: './teacher-class-detail.component.scss'
})
export class TeacherClassDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private classService = inject(TeacherClassService);
  private videoResultService = inject(VideoResultService);
  private toastService = inject(ToastService);

  // Active class ID
  classId = signal<string>('');

  activeTab = signal<ClassTab>('students');

  // Filter state for students
  studentSearch = signal<string>('');
  studentStatusFilter = signal<string>('all');

  statusFilterOptions: SelectOption[] = [
    { label: 'Tất cả sinh viên', value: 'all' },
    { label: 'Đạt yêu cầu', value: 'pass' },
    { label: 'Chưa đạt / Cần thi lại', value: 'fail' },
    { label: 'Cảnh báo điểm thấp', value: 'warning' }
  ];

  // Modals
  isFinalizeModalOpen = signal<boolean>(false);
  hasFinalizeConfirmedCheck = signal<boolean>(false);

  // Instruction Video Modals & State
  isInstructionUploadModalOpen = signal<boolean>(false);
  isInstructionPreviewModalOpen = signal<boolean>(false);
  selectedInstructionTask = signal<GradebookTaskItem | null>(null);
  selectedInstructionFile = signal<File | null>(null);
  instructionUploadProgress = signal<number>(0);
  isInstructionUploading = signal<boolean>(false);
  instructionUploadError = signal<string | null>(null);

  // Nhập điểm một sinh viên (điểm nhập tay từng bài, chuyên cần, ghi chú)
  scoreStudent = signal<GradebookStudentItem | null>(null);
  scoreDraft = signal<{ [taskId: string]: number | null }>({});
  attendanceDraft = signal<number | null>(null);
  noteDraft = signal<string>('');
  savingScores = signal(false);

  // Duyệt bài nộp & form bài kiểm tra
  reviewTaskId = signal<string | null>(null);
  taskFormOpen = signal(false);
  editingTask = signal<GradebookTaskItem | null>(null);

  currentDetail = this.classService.currentDetail;
  currentGradebook = this.classService.currentGradebook;

  // Filtered students
  filteredStudents = computed(() => {
    const gb = this.currentGradebook();
    if (!gb) return [];

    let list = gb.students;

    // Search filter
    const kw = this.studentSearch().toLowerCase().trim();
    if (kw) {
      list = list.filter(
        s =>
          (s.student_name && s.student_name.toLowerCase().includes(kw)) ||
          (s.student_code && s.student_code.toLowerCase().includes(kw))
      );
    }

    // Status filter
    const status = this.studentStatusFilter();
    if (status !== 'all') {
      if (status === 'pass') list = list.filter(s => s.grades.is_passed === true);
      else if (status === 'fail') list = list.filter(s => s.grades.is_passed === false);
    }

    return list;
  });

  // Statistics
  classStats = computed(() => {
    const gb = this.currentGradebook();
    if (!gb) return null;
    const students = gb.students;
    const total = students.length;
    const passed = students.filter(s => s.grades.is_passed === true).length;
    const failed = students.filter(s => s.grades.is_passed === false).length;

    const scores = students
      .map(s => s.grades.final_score)
      .filter((s): s is number => s !== null && s !== undefined);
    const avgClass = scores.length > 0
      ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
      : '0.0';

    return {
      total,
      passed,
      failed,
      avgScore: avgClass,
      passRate: total > 0 ? Math.round((passed / total) * 100) : 0
    };
  });

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.classId.set(id);
        this.classService.loadCourseDetail(id).subscribe();
        this.classService.loadGradebook(id).subscribe();
      }
    });
  }

  goBack(): void {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      this.router.navigate(['/teacher/classes']);
    }
  }

  setTab(tab: ClassTab): void {
    this.activeTab.set(tab);
  }

  pendingReviewTotal = computed(() =>
    (this.currentGradebook()?.task_list || []).reduce((sum, t) => sum + (t.pending_review_count || 0), 0)
  );

  reloadGradebook(): void {
    const id = this.classId();
    if (id) this.classService.loadGradebook(id).subscribe();
  }

  kindLabel(kind: TaskKind): string {
    return kind === 'final' ? 'Thi kết thúc' : kind === 'midterm' ? 'Thi giữa kỳ' : 'Thường xuyên';
  }

  methodLabel(method?: GradingMethod): string {
    return method === 'latest' ? 'Lấy lần nộp gần nhất' : method === 'average' ? 'Lấy trung bình' : 'Lấy lần cao nhất';
  }

  /** "TX1: Kỹ thuật ..." -> "TX1"; tiêu đề không có tiền tố thì cắt ngắn. */
  shortTaskTitle(task: GradebookTaskItem): string {
    const prefix = task.title.split(':')[0].trim();
    return prefix.length <= 16 ? prefix : prefix.slice(0, 14) + '…';
  }

  effectiveTaskScore(student: GradebookStudentItem, taskId: string): number | undefined {
    return student.task_score_overrides?.[taskId] ?? student.task_scores?.[taskId];
  }

  // --- DUYỆT BÀI NỘP ---

  openReview(taskId: string | null): void {
    this.reviewTaskId.set(taskId);
    this.activeTab.set('review');
  }

  openReviewFor(taskId: string): void {
    this.closeScoreModal();
    this.openReview(taskId);
  }

  // --- BÀI KIỂM TRA ---

  openTaskForm(task: GradebookTaskItem | null): void {
    this.editingTask.set(task);
    this.taskFormOpen.set(true);
  }

  onTaskSaved(): void {
    this.taskFormOpen.set(false);
    this.reloadGradebook();
  }

  deleteTask(task: GradebookTaskItem): void {
    const cls = this.currentDetail();
    if (!cls || !confirm(`Xóa bài "${task.title}"?`)) return;
    this.classService.deleteTask(cls.id, task.id).subscribe({
      next: () => {
        this.toastService.success('Đã xóa bài kiểm tra.');
        this.reloadGradebook();
      },
      error: (err) => this.toastService.error(err?.error?.message || 'Không xóa được bài kiểm tra.')
    });
  }

  // --- ACTIONS: LOCK PRACTICE & LOCK SUBMISSIONS ---

  togglePracticeLock(): void {
    const cls = this.currentDetail();
    if (!cls) return;

    if (cls.is_grade_locked) {
      this.toastService.warning('Lớp học phần đã chốt điểm, không thể thay đổi trạng thái luyện tập!');
      return;
    }

    const newAllowPractice = !cls.allow_practice_submission;
    this.classService.toggleSubmissionLock(cls.id, newAllowPractice, cls.allow_exam_submission).subscribe({
      next: () => {
        const msg = !newAllowPractice
          ? 'Đã KHÓA tính năng luyện tập của lớp này.'
          : 'Đã MỞ tính năng luyện tập cho sinh viên.';
        this.toastService.success(msg);
        this.classService.loadCourseDetail(cls.id).subscribe();
      },
      error: (err) => this.toastService.error('Lỗi khi cập nhật trạng thái.')
    });
  }

  toggleSubmissionLock(): void {
    const cls = this.currentDetail();
    if (!cls) return;

    if (cls.is_grade_locked) {
      this.toastService.warning('Lớp học phần đã chốt điểm, không thể thay đổi trạng thái nộp bài!');
      return;
    }

    const newAllowExam = !cls.allow_exam_submission;
    this.classService.toggleSubmissionLock(cls.id, cls.allow_practice_submission, newAllowExam).subscribe({
      next: () => {
        const msg = !newAllowExam
          ? 'Đã KHÓA quyền nộp bài kiểm tra trong lớp.'
          : 'Đã MỞ quyền nộp bài cho sinh viên.';
        this.toastService.success(msg);
        this.classService.loadCourseDetail(cls.id).subscribe();
      },
      error: (err) => this.toastService.error('Lỗi khi cập nhật trạng thái.')
    });
  }

  // --- ACTION: FINALIZE GRADES (CHỐT ĐIỂM) ---

  openFinalizeModal(): void {
    const cls = this.currentDetail();
    if (!cls) return;

    if (cls.is_grade_locked) {
      this.toastService.info('Lớp học phần này đã được chốt điểm.');
      return;
    }

    this.hasFinalizeConfirmedCheck.set(false);
    this.isFinalizeModalOpen.set(true);
  }

  closeFinalizeModal(): void {
    this.isFinalizeModalOpen.set(false);
  }

  executeFinalizeGrades(): void {
    const cls = this.currentDetail();
    if (!cls) return;

    this.classService.finalizeClassGrades(cls.id).subscribe({
      next: () => {
        this.isFinalizeModalOpen.set(false);
        this.toastService.success('CHỐT ĐIỂM THÀNH CÔNG! Toàn bộ bảng điểm đã được khóa và lưu trữ chính thức.');
        this.classService.loadCourseDetail(cls.id).subscribe();
        this.classService.loadGradebook(cls.id).subscribe();
      },
      error: (err) => this.toastService.error(err?.error?.message || 'Lỗi khi chốt điểm')
    });
  }

  unlockGradesForCorrection(): void {
    const cls = this.currentDetail();
    if (!cls) return;

    this.classService.reopenClassGrades(cls.id).subscribe({
      next: () => {
        this.toastService.success('Đã mở khóa bảng điểm để giáo viên hiệu chỉnh lại.');
        this.classService.loadCourseDetail(cls.id).subscribe();
        this.classService.loadGradebook(cls.id).subscribe();
      },
      error: () => this.toastService.error('Lỗi khi mở khóa bảng điểm')
    });
  }

  // --- NHẬP ĐIỂM SINH VIÊN ---

  openScoreModal(student: GradebookStudentItem): void {
    const gb = this.currentGradebook();
    const draft: { [taskId: string]: number | null } = {};
    gb?.task_list.forEach((t) => (draft[t.id] = student.task_score_overrides?.[t.id] ?? null));
    this.scoreDraft.set(draft);
    this.attendanceDraft.set(student.grades.attendance_score ?? null);
    this.noteDraft.set(student.note || '');
    this.scoreStudent.set(student);
  }

  closeScoreModal(): void {
    if (!this.savingScores()) this.scoreStudent.set(null);
  }

  setDraft(taskId: string, value: number | string | null): void {
    const v = value === '' || value === null || value === undefined ? null : Number(value);
    this.scoreDraft.update((d) => ({ ...d, [taskId]: v }));
  }

  saveScores(): void {
    const student = this.scoreStudent();
    const cls = this.currentDetail();
    const gb = this.currentGradebook();
    if (!student || !cls || !gb) return;

    const invalid = (v: number | null) => v !== null && (isNaN(v) || v < 0 || v > 10);
    const draft = this.scoreDraft();
    const attendance = this.attendanceDraft() === null || (this.attendanceDraft() as unknown) === '' ? null : Number(this.attendanceDraft());
    if (Object.values(draft).some(invalid) || invalid(attendance)) {
      this.toastService.warning('Điểm phải từ 0 đến 10.');
      return;
    }

    const requests: Observable<any>[] = [];
    gb.task_list.forEach((t) => {
      const before = student.task_score_overrides?.[t.id] ?? null;
      if (draft[t.id] !== before) {
        requests.push(this.classService.setTaskScore(cls.id, student.enrollment_id, t.id, draft[t.id]));
      }
    });
    const attendanceChanged = !gb.attendance_from_sessions && attendance !== null && attendance !== (student.grades.attendance_score ?? null);
    const noteChanged = this.noteDraft() !== (student.note || '');
    if (attendanceChanged || noteChanged) {
      requests.push(this.classService.batchUpdateGrades(cls.id, [{
        enrollment_id: student.enrollment_id,
        attendance_score: attendanceChanged ? attendance : undefined,
        note: noteChanged ? this.noteDraft() : undefined
      }]));
    }
    if (!requests.length) {
      this.scoreStudent.set(null);
      return;
    }

    this.savingScores.set(true);
    // Lần lượt để các lần tính lại điểm không ghi đè nhau
    requests.reduce((chain, req) => chain.then(() => new Promise((res, rej) => req.subscribe({ next: res, error: rej }))), Promise.resolve() as Promise<unknown>)
      .then(() => {
        this.savingScores.set(false);
        this.scoreStudent.set(null);
        this.toastService.success(`Đã lưu điểm cho ${student.student_name}.`);
        this.reloadGradebook();
      })
      .catch((err) => {
        this.savingScores.set(false);
        this.toastService.error(err?.error?.message || 'Lỗi khi lưu điểm.');
        this.reloadGradebook();
      });
  }

  /** Xuất bảng điểm ra CSV (UTF-8 có BOM để Excel hiển thị đúng tiếng Việt). */
  exportExcel(): void {
    const gb = this.currentGradebook();
    const cls = this.currentDetail();
    if (!gb || !cls) return;
    const esc = (v: unknown) => {
      const text = v === null || v === undefined ? '' : String(v);
      return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    };
    const header = ['STT', 'Mã SV', 'Họ và tên', ...gb.task_list.map((t) => t.title),
      'Chuyên cần', 'Quá trình', 'Thi', 'Tổng kết', 'Điểm chữ', 'Đủ ĐK dự thi', 'Ghi chú'];
    const rows = gb.students.map((st, i) => [
      i + 1, st.student_code, st.student_name,
      ...gb.task_list.map((t) => this.effectiveTaskScore(st, t.id)),
      st.grades.attendance_score, st.grades.process_score, st.grades.exam_score, st.grades.final_score,
      st.grades.letter_grade, st.grades.is_eligible === false ? 'Không' : 'Có', st.note
    ]);
    const csv = [header, ...rows].map((r) => r.map(esc).join(',')).join('\r\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bang-diem-${cls.code || cls.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // --- INSTRUCTION VIDEO MANAGEMENT ---

  openInstructionUpload(task: GradebookTaskItem): void {
    this.selectedInstructionTask.set(task);
    this.selectedInstructionFile.set(null);
    this.instructionUploadProgress.set(0);
    this.instructionUploadError.set(null);
    this.isInstructionUploading.set(false);
    this.isInstructionUploadModalOpen.set(true);
  }

  closeInstructionUpload(): void {
    if (this.isInstructionUploading()) return;
    this.isInstructionUploadModalOpen.set(false);
    this.selectedInstructionFile.set(null);
    this.instructionUploadProgress.set(0);
    this.instructionUploadError.set(null);
  }

  onInstructionFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    const validExtensions = ['.mp4', '.webm', '.mov', '.mkv'];
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!validExtensions.includes(ext)) {
      this.instructionUploadError.set(`Định dạng file không được hỗ trợ (${ext}). Vui lòng chọn file MP4 hoặc WebM.`);
      this.selectedInstructionFile.set(null);
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      this.instructionUploadError.set('Dung lượng video không được vượt quá 100MB.');
      this.selectedInstructionFile.set(null);
      return;
    }

    this.instructionUploadError.set(null);
    this.selectedInstructionFile.set(file);
  }

  uploadInstructionVideo(): void {
    const task = this.selectedInstructionTask();
    const file = this.selectedInstructionFile();
    if (!task || !file) {
      this.toastService.warning('Vui lòng chọn file video trước khi tải lên.');
      return;
    }

    this.isInstructionUploading.set(true);
    this.instructionUploadProgress.set(0);
    this.instructionUploadError.set(null);

    this.classService.uploadInstructionVideo(task.id, file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          const percent = Math.round((100 * event.loaded) / event.total);
          this.instructionUploadProgress.set(percent);
        } else if (event.type === HttpEventType.Response) {
          this.isInstructionUploading.set(false);
          this.toastService.success(`Đã tải lên video hướng dẫn cho bài "${task.title}" thành công!`);
          this.closeInstructionUpload();
          this.classService.loadGradebook(this.classId()).subscribe();
        }
      },
      error: (err) => {
        this.isInstructionUploading.set(false);
        const errMsg = err.error?.detail || 'Lỗi khi tải video lên server. Vui lòng thử lại.';
        this.instructionUploadError.set(errMsg);
        this.toastService.error(errMsg);
      }
    });
  }

  openInstructionPreview(task: GradebookTaskItem): void {
    this.selectedInstructionTask.set(task);
    this.isInstructionPreviewModalOpen.set(true);
  }

  closeInstructionPreview(): void {
    this.isInstructionPreviewModalOpen.set(false);
  }

  confirmDeleteInstructionVideo(task: GradebookTaskItem): void {
    if (!confirm(`Bạn có chắc chắn muốn xóa video hướng dẫn của bài kiểm tra "${task.title}"?`)) {
      return;
    }

    this.classService.deleteInstructionVideo(task.id).subscribe({
      next: () => {
        this.toastService.success(`Đã xóa video hướng dẫn của bài "${task.title}".`);
        this.closeInstructionPreview();
        this.classService.loadGradebook(this.classId()).subscribe();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Lỗi khi xóa video hướng dẫn');
      }
    });
  }
}

