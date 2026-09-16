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
  LucideClock,
  LucideAlertCircle,
  LucideCheck,
  LucideX,
  LucideEdit3,
  LucideDumbbell,
  LucideFootprints,
  LucideActivity,
  LucideShieldAlert
} from '@lucide/angular';
import {
  SearchInputComponent,
  SelectComponent,
  SelectOption
} from '@shared/components';
import { TeacherClassService } from '../services/teacher-class.service';
import {
  TeacherClass,
  StudentGradeRecord,
  ClassAssessment,
  StudentSubmission
} from '../models/teacher.model';

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
    LucideClock,
    LucideAlertCircle,
    LucideCheck,
    LucideX,
    LucideEdit3,
    LucideDumbbell,
    LucideFootprints,
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
  selectedStudentForDetail = signal<StudentGradeRecord | null>(null);
  selectedAssessmentForDetail = signal<ClassAssessment | null>(null);
  currentSubmissionDetail = signal<StudentSubmission | null>(null);
  editScoreValue = signal<number | null>(null);
  editCommentValue = signal<string>('');

  // Toast
  toastMessage = signal<string>('');
  toastType = signal<'success' | 'warning' | 'info'>('success');
  isToastVisible = signal<boolean>(false);
  private toastTimer: any = null;

  // Retrieve current class from service reactive state
  currentClass = computed(() => {
    const id = this.classId();
    return this.classService.getClassById(id);
  });

  // Filtered students
  filteredStudents = computed(() => {
    const cls = this.currentClass();
    if (!cls) return [];

    let list = cls.students;

    // Search filter
    const kw = this.studentSearch().toLowerCase().trim();
    if (kw) {
      list = list.filter(
        s =>
          s.fullName.toLowerCase().includes(kw) ||
          s.studentCode.toLowerCase().includes(kw) ||
          s.majorClass.toLowerCase().includes(kw)
      );
    }

    // Status filter
    const status = this.studentStatusFilter();
    if (status !== 'all') {
      list = list.filter(s => s.resultStatus === status);
    }

    return list;
  });

  // Statistics
  classStats = computed(() => {
    const cls = this.currentClass();
    if (!cls) return null;
    const students = cls.students;
    const total = students.length;
    const passed = students.filter(s => s.resultStatus === 'pass').length;
    const failed = students.filter(s => s.resultStatus === 'fail').length;
    const warning = students.filter(s => s.resultStatus === 'warning').length;

    const scores = students
      .map(s => s.finalAvgScore)
      .filter((s): s is number => s !== null && s !== undefined);
    const avgClass = scores.length > 0
      ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
      : '0.0';

    return {
      total,
      passed,
      failed,
      warning,
      avgScore: avgClass,
      passRate: total > 0 ? Math.round((passed / total) * 100) : 0
    };
  });

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id) {
        this.classId.set(id);
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
    const cls = this.currentClass();
    if (!cls) return;

    if (cls.isFinalized) {
      this.showToast('Lớp học phần đã chốt điểm, không thể thay đổi trạng thái luyện tập!', 'warning');
      return;
    }

    const isLocked = this.classService.togglePracticeLock(cls.id);
    const msg = isLocked
      ? 'Đã KHÓA tính năng luyện tập của lớp này.'
      : 'Đã MỞ tính năng luyện tập cho sinh viên.';
    this.showToast(msg, isLocked ? 'warning' : 'success');
  }

  toggleSubmissionLock(): void {
    const cls = this.currentClass();
    if (!cls) return;

    if (cls.isFinalized) {
      this.showToast('Lớp học phần đã chốt điểm, không thể thay đổi trạng thái nộp bài!', 'warning');
      return;
    }

    const isLocked = this.classService.toggleSubmissionLock(cls.id);
    const msg = isLocked
      ? 'Đã KHÓA quyền nộp bài cho toàn bộ bài kiểm tra trong lớp.'
      : 'Đã MỞ quyền nộp bài cho sinh viên.';
    this.showToast(msg, isLocked ? 'warning' : 'success');
  }

  toggleSingleAssessmentLock(assessment: ClassAssessment): void {
    const cls = this.currentClass();
    if (!cls) return;

    if (cls.isFinalized) {
      this.showToast('Lớp học phần đã chốt điểm, không thể thay đổi trạng thái!', 'warning');
      return;
    }

    const isLocked = this.classService.toggleAssessmentLock(cls.id, assessment.id);
    const msg = isLocked
      ? `Đã KHÓA nộp bài cho ${assessment.name}.`
      : `Đã MỞ nộp bài cho ${assessment.name}.`;
    this.showToast(msg, isLocked ? 'warning' : 'success');
  }

  // --- ACTION: FINALIZE GRADES (CHỐT ĐIỂM) ---

  openFinalizeModal(): void {
    const cls = this.currentClass();
    if (!cls) return;

    if (cls.isFinalized) {
      // Reopen toggle or alert
      this.showToast('Lớp học phần này đã được chốt điểm.', 'info');
      return;
    }

    this.hasFinalizeConfirmedCheck.set(false);
    this.isFinalizeModalOpen.set(true);
  }

  closeFinalizeModal(): void {
    this.isFinalizeModalOpen.set(false);
  }

  executeFinalizeGrades(): void {
    const cls = this.currentClass();
    if (!cls) return;

    this.classService.finalizeClassGrades(cls.id, 'ThS. Đặng Văn Long');
    this.isFinalizeModalOpen.set(false);
    this.showToast('CHỐT ĐIỂM THÀNH CÔNG! Toàn bộ bảng điểm đã được khóa và lưu trữ chính thức.', 'success');
  }

  unlockGradesForCorrection(): void {
    const cls = this.currentClass();
    if (!cls) return;

    this.classService.reopenClassGrades(cls.id);
    this.showToast('Đã mở khóa bảng điểm để giáo viên hiệu chỉnh lại.', 'warning');
  }

  // --- STUDENT SUBMISSION MODAL ---

  openSubmissionModal(student: StudentGradeRecord, assessmentType: string = 'tx1'): void {
    this.selectedStudentForDetail.set(student);
    const cls = this.currentClass();
    const assessment = cls?.assessments.find(a => a.id === assessmentType) || cls?.assessments[0] || null;
    this.selectedAssessmentForDetail.set(assessment);

    const submission = student.submissions?.[assessmentType] || null;
    this.currentSubmissionDetail.set(submission);
    this.editScoreValue.set(submission?.teacherScore ?? submission?.aiScore ?? null);
    this.editCommentValue.set(submission?.teacherComment ?? '');

    this.isSubmissionModalOpen.set(true);
  }

  closeSubmissionModal(): void {
    this.isSubmissionModalOpen.set(false);
  }

  switchAssessmentInModal(assessmentId: string): void {
    const student = this.selectedStudentForDetail();
    if (!student) return;
    const cls = this.currentClass();
    const assessment = cls?.assessments.find(a => a.id === assessmentId) || null;
    this.selectedAssessmentForDetail.set(assessment);

    const submission = student.submissions?.[assessmentId] || null;
    this.currentSubmissionDetail.set(submission);
    this.editScoreValue.set(submission?.teacherScore ?? submission?.aiScore ?? null);
    this.editCommentValue.set(submission?.teacherComment ?? '');
  }

  saveTeacherGrading(): void {
    const student = this.selectedStudentForDetail();
    const assessment = this.selectedAssessmentForDetail();
    const cls = this.currentClass();
    if (!student || !assessment || !cls) return;

    const score = this.editScoreValue();
    if (score !== null && (score < 0 || score > 10)) {
      this.showToast('Điểm số phải từ 0 đến 10!', 'warning');
      return;
    }

    // Map assessment id to field
    let field: 'tx1Score' | 'tx2Score' | 'midtermScore' | 'finalScore' = 'tx1Score';
    if (assessment.id === 'tx2') field = 'tx2Score';
    else if (assessment.id === 'midterm') field = 'midtermScore';
    else if (assessment.id === 'final') field = 'finalScore';

    this.classService.updateStudentScore(cls.id, student.id, field, score);
    this.isSubmissionModalOpen.set(false);
    this.showToast(`Đã lưu điểm cho sinh viên ${student.fullName}.`, 'success');
  }

  exportExcel(): void {
    this.showToast('Đang tạo và tải về bảng điểm Excel của lớp học phần...', 'info');
  }

  private showToast(msg: string, type: 'success' | 'warning' | 'info' = 'success'): void {
    this.toastMessage.set(msg);
    this.toastType.set(type);
    this.isToastVisible.set(true);

    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => {
      this.isToastVisible.set(false);
    }, 3500);
  }
}
