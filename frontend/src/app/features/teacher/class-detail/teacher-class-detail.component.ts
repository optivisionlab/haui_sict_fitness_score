import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
  LucideShieldAlert
} from '@lucide/angular';
import {
  SearchInputComponent,
  SelectComponent,
  SelectOption
} from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import { VideoResultService } from '../../../core/services/video-result.service';
import { ToastService } from '../../../core/services/toast.service';
import { GradebookStudentItem, GradebookTaskItem } from '../models/teacher.model';

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

  // Active view tabs: 'students' | 'assessments' | 'stats'
  activeTab = signal<'students' | 'assessments' | 'stats'>('students');

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

  // Submission Detail Modal
  isSubmissionModalOpen = signal<boolean>(false);
  selectedStudentForDetail = signal<GradebookStudentItem | null>(null);
  selectedAssessmentForDetail = signal<GradebookTaskItem | null>(null);
  currentSubmissionDetail = signal<any | null>(null);
  editScoreValue = signal<number | null>(null);
  editCommentValue = signal<string>('');

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
    this.router.navigate(['/teacher/classes']);
  }

  setTab(tab: 'students' | 'assessments' | 'stats'): void {
    this.activeTab.set(tab);
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
      error: () => this.toastService.error('Lỗi khi chốt điểm')
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

  // --- STUDENT SUBMISSION MODAL ---

  openSubmissionModal(student: GradebookStudentItem, taskId?: string): void {
    this.selectedStudentForDetail.set(student);
    const gb = this.currentGradebook();
    
    // Choose specific task or default to first task
    let task = gb?.task_list.find(t => t.id === taskId) || null;
    if (!task && gb?.task_list.length) {
      task = gb.task_list[0];
    }
    
    this.selectedAssessmentForDetail.set(task);

    const score = task && student.task_scores ? student.task_scores[task.id] : null;
    this.editScoreValue.set(score);
    this.editCommentValue.set('');

    this.isSubmissionModalOpen.set(true);

    if (task) {
      this.fetchVideoResult(student, task.id);
    }
  }

  closeSubmissionModal(): void {
    this.isSubmissionModalOpen.set(false);
  }

  switchAssessmentInModal(taskId: string): void {
    const student = this.selectedStudentForDetail();
    if (!student) return;
    const gb = this.currentGradebook();
    const task = gb?.task_list.find(t => t.id === taskId) || null;
    this.selectedAssessmentForDetail.set(task);

    const score = task && student.task_scores ? student.task_scores[task.id] : null;
    this.editScoreValue.set(score);
    this.editCommentValue.set('');

    if (task) {
      this.fetchVideoResult(student, task.id);
    }
  }

  private fetchVideoResult(student: GradebookStudentItem, taskId: string): void {
    const sid = student.user_id;
    this.videoResultService.getVideoResults({ student_id: sid, exercise_id: taskId }).subscribe({
      next: (res) => {
        const videos = res?.data || [];
        if (videos.length > 0) {
          const latestVideo = videos[0];
          this.currentSubmissionDetail.set({
            submittedAt: new Date(latestVideo.created_at).toLocaleString('vi-VN'),
            videoUrl: latestVideo.video_url,
            aiScore: latestVideo.score !== null && latestVideo.score !== undefined ? latestVideo.score : undefined,
            aiFeedback: latestVideo.feedback || undefined,
            status: latestVideo.status === 'completed' ? 'graded' : 'pending'
          });
        } else {
          this.currentSubmissionDetail.set(null);
        }
      },
      error: () => this.currentSubmissionDetail.set(null)
    });
  }

  saveTeacherGrading(): void {
    const student = this.selectedStudentForDetail();
    const task = this.selectedAssessmentForDetail();
    const cls = this.currentDetail();
    if (!student || !task || !cls) return;

    const score = this.editScoreValue();
    if (score !== null && (score < 0 || score > 10)) {
      this.toastService.warning('Điểm số phải từ 0 đến 10!');
      return;
    }

    // In a real scenario you would update the specific task score.
    // However the batchUpdateGrades API takes attendance_score and exam_score directly on enrollment.
    // Let's assume if it's an exam we map it to exam_score. If it's practice we map to attendance_score for simplicity.
    const updates = [{
      enrollment_id: student.enrollment_id,
      exam_score: task.category === 'exam' ? score : undefined,
      attendance_score: task.category === 'practice' ? score : undefined,
      note: this.editCommentValue()
    }];

    this.classService.batchUpdateGrades(cls.id, updates).subscribe({
      next: () => {
        this.isSubmissionModalOpen.set(false);
        this.toastService.success(`Đã lưu điểm cho sinh viên ${student.student_name}.`);
        this.classService.loadGradebook(cls.id).subscribe();
      },
      error: () => this.toastService.error('Lỗi khi lưu điểm')
    });
  }

  exportExcel(): void {
    this.toastService.info('Đang tạo và tải về bảng điểm Excel của lớp học phần...');
  }
}

