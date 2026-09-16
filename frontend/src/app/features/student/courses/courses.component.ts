import { Component, signal, computed, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import {
  LucideDumbbell,
  LucideFootprints,
  LucideUser,
  LucideUploadCloud,
  LucideX,
  LucideChevronRight,
  LucideFileText,
  LucideCheckCircle2,
  LucideClock,
  LucideAlertCircle,
  LucideArrowLeft
} from '@lucide/angular';
import { SearchInputComponent } from '@shared/components';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/auth.model';
import {
  Course,
  CourseDetailInfo,
  AssessmentItem,
  AssessmentAttempt
} from './models/course-detail.model';

@Component({
  selector: 'app-courses',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideDumbbell,
    LucideFootprints,
    LucideUser,
    LucideUploadCloud,
    LucideX,
    LucideChevronRight,
    LucideFileText,
    LucideCheckCircle2,
    LucideClock,
    LucideAlertCircle,
    LucideArrowLeft,
    SearchInputComponent
  ],
  templateUrl: './courses.component.html',
  styleUrl: './courses.component.scss'
})
export class CoursesComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);

  // Navigation views: 'list' (danh sách môn) | 'course' (môn học - danh sách bài) | 'assessment' (chi tiết bài nộp)
  activeView = signal<'list' | 'course' | 'assessment'>('list');

  // List filter state
  selectedTab = signal<'all' | 'active' | 'done'>('all');
  searchKeyword = signal<string>('');

  // Selected state
  selectedCourseId = signal<string>('pickleball');
  selectedAssessmentId = signal<string>('tx1');

  // Modals
  isSubmitModalOpen = signal<boolean>(false);
  isReviewModalOpen = signal<boolean>(false);
  selectedFileName = signal<string>('');
  hasVideoSelected = signal<boolean>(false);
  submitNote = signal<string>('');
  selectedAttempt = signal<AssessmentAttempt | null>(null);

  // Toast
  toastMessage = signal<string>('');
  isToastVisible = signal<boolean>(false);
  private toastTimer: any = null;

  // Base courses list
  courses = signal<Course[]>([
    {
      id: 'pickleball',
      name: 'Pickleball',
      teacher: 'Đặng Văn Long',
      startDate: '01/09/2026',
      endDate: '15/11/2026',
      examDate: '20/11/2026',
      progress: 50,
      status: 'active',
      iconType: 'pickleball',
      averageScore: 8.5
    },
    {
      id: 'chay',
      name: 'Chạy',
      teacher: 'Vũ Thị Lan',
      startDate: '01/09/2026',
      endDate: '30/10/2026',
      examDate: '05/11/2026',
      progress: 75,
      status: 'active',
      iconType: 'chay',
      averageScore: 9.0
    }
  ]);

  // Course Details dictionary with 4 assessments: TX1, TX2, Giữa kỳ, Cuối kỳ
  courseDetails = signal<Record<string, CourseDetailInfo>>({
    pickleball: {
      id: 'pickleball',
      title: 'Pickleball',
      teacher: 'Đặng Văn Long',
      dates: '01/09/2026 - 15/11/2026',
      examDate: '20/11/2026',
      progress: 50,
      code: '20261PB0001_TX001',
      desc: 'Học phần trang bị cho sinh viên kỹ thuật cơ bản môn Pickleball. Đánh giá kết quả học tập qua hình thức nộp video thực hành để hệ thống chấm điểm.',
      thumbClass: '',
      thumbIcon: 'pickleball',
      averageScore: 8.5,
      assessments: [
        {
          id: 'tx1',
          name: 'Bài thường xuyên 1 (TX1) - Kỹ thuật giao bóng',
          type: 'tx1',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '01/09/2026',
          closeTime: '20/09/2026 23:59',
          status: 'graded',
          score: 8.5,
          attempts: [
            { attemptNo: 1, date: '15/09/2026 - 14:32:05', duration: '00:00:12', score: 8.5 }
          ]
        },
        {
          id: 'tx2',
          name: 'Bài thường xuyên 2 (TX2) - Kỹ thuật đỡ bóng & di chuyển',
          type: 'tx2',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '10/09/2026',
          closeTime: '30/09/2026 23:59',
          status: 'graded',
          score: 8.5,
          attempts: [
            { attemptNo: 1, date: '18/09/2026 - 10:15:22', duration: '00:00:15', score: 8.5 }
          ]
        },
        {
          id: 'giua-ky',
          name: 'Bài giữa kỳ - Phối hợp đánh đôi & chiến thuật',
          type: 'midterm',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '01/10/2026',
          closeTime: '20/10/2026 23:59',
          status: 'not_submitted',
          attempts: []
        },
        {
          id: 'cuoi-ky',
          name: 'Bài cuối kỳ - Thi đấu tính điểm chính thức',
          type: 'final',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '01/11/2026',
          closeTime: '20/11/2026 23:59',
          status: 'not_submitted',
          attempts: []
        }
      ]
    },
    chay: {
      id: 'chay',
      title: 'Chạy',
      teacher: 'Vũ Thị Lan',
      dates: '01/09/2026 - 30/10/2026',
      examDate: '05/11/2026',
      progress: 75,
      code: '20261TD0002_TX001',
      desc: 'Học phần rèn luyện thể lực nền tảng qua các bài chạy bền và chạy tốc độ. Đánh giá kết quả qua video quay lại quá trình thực hiện bài chạy.',
      thumbClass: 'teal',
      thumbIcon: 'chay',
      averageScore: 9.0,
      assessments: [
        {
          id: 'tx1',
          name: 'Bài thường xuyên 1 (TX1) - Chạy cự ly ngắn (60m - 100m)',
          type: 'tx1',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '01/09/2026',
          closeTime: '15/09/2026 23:59',
          status: 'graded',
          score: 9.0,
          attempts: [
            { attemptNo: 1, date: '12/09/2026 - 08:30:10', duration: '00:00:14', score: 9.0 }
          ]
        },
        {
          id: 'tx2',
          name: 'Bài thường xuyên 2 (TX2) - Chạy bền 1500m',
          type: 'tx2',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '16/09/2026',
          closeTime: '30/09/2026 23:59',
          status: 'graded',
          score: 9.0,
          attempts: [
            { attemptNo: 1, date: '25/09/2026 - 16:45:00', duration: '00:06:20', score: 9.0 }
          ]
        },
        {
          id: 'giua-ky',
          name: 'Bài giữa kỳ - Kỹ thuật tiếp sức & xuất phát',
          type: 'midterm',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '05/10/2026',
          closeTime: '15/10/2026 23:59',
          status: 'graded',
          score: 9.0,
          attempts: [
            { attemptNo: 1, date: '10/10/2026 - 09:00:00', duration: '00:00:30', score: 9.0 }
          ]
        },
        {
          id: 'cuoi-ky',
          name: 'Bài cuối kỳ - Kiểm tra chạy bền tiêu chuẩn',
          type: 'final',
          gradingMethod: 'Lần cao nhất',
          timeLimit: 'Không giới hạn',
          openTime: '25/10/2026',
          closeTime: '05/11/2026 23:59',
          status: 'not_submitted',
          attempts: []
        }
      ]
    }
  });

  ngOnInit(): void {
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/enrollments/my-courses`).subscribe({
      next: (res) => {
        const items = res?.data?.items || [];
        if (items.length > 0) {
          const mappedCourses: Course[] = items.map((e: any) => {
            const isBadminton = e.courseName?.toLowerCase().includes('cầu lông') || e.courseName?.toLowerCase().includes('badminton');
            return {
              id: e.courseId,
              name: e.courseName,
              teacher: e.teacherName || 'ThS. Trần Thị Bình',
              startDate: '01/09/2026',
              endDate: '15/12/2026',
              examDate: '23/11/2026',
              progress: Math.round(e.progressPercent || 0),
              status: 'active',
              iconType: isBadminton ? 'pickleball' : 'chay',
              averageScore: e.grades?.finalScore ?? (e.grades?.processScore ?? 8.5)
            };
          });
          this.courses.set(mappedCourses);
          this.selectedCourseId.set(mappedCourses[0].id);

          const detailsMap: Record<string, CourseDetailInfo> = {};
          mappedCourses.forEach(c => {
            detailsMap[c.id] = {
              id: c.id,
              title: c.name,
              teacher: c.teacher,
              dates: '01/09/2026 - 15/12/2026',
              examDate: c.examDate,
              progress: c.progress,
              code: c.id.substring(0, 10).toUpperCase(),
              desc: 'Học phần giáo dục thể chất đào tạo kỹ thuật chuyên môn và rèn luyện thể lực. Chấm điểm và đánh giá tự động qua video bằng AI.',
              thumbClass: '',
              thumbIcon: c.iconType,
              averageScore: c.averageScore,
              assessments: [
                {
                  id: 'tx1',
                  name: 'Bài thường xuyên 1 (TX1) - Kỹ thuật cơ bản',
                  type: 'tx1',
                  gradingMethod: 'Lần cao nhất',
                  timeLimit: 'Không giới hạn',
                  openTime: '01/09/2026 08:00',
                  closeTime: '30/10/2026 23:59',
                  status: 'graded',
                  score: 8.8,
                  attempts: [
                    { attemptNo: 1, date: '10/09/2026 14:32', duration: '0:45', score: 8.8 }
                  ]
                },
                {
                  id: 'tx2',
                  name: 'Bài thường xuyên 2 (TX2) - Kỹ thuật nâng cao',
                  type: 'tx2',
                  gradingMethod: 'Lần cao nhất',
                  timeLimit: 'Không giới hạn',
                  openTime: '15/09/2026 08:00',
                  closeTime: '15/11/2026 23:59',
                  status: 'graded',
                  score: 8.2,
                  attempts: [
                    { attemptNo: 1, date: '20/09/2026 09:15', duration: '1:02', score: 8.2 }
                  ]
                },
                {
                  id: 'final',
                  name: 'Thi kết thúc học phần',
                  type: 'final',
                  gradingMethod: 'Lần cao nhất',
                  timeLimit: '60 phút',
                  openTime: '20/11/2026 07:00',
                  closeTime: '23/11/2026 17:00',
                  status: 'not_submitted',
                  attempts: []
                }
              ]
            };
          });
          this.courseDetails.set(detailsMap);
        }
      },
      error: () => {}
    });
  }

  // Current active course info
  currentCourse = computed(() => {
    return this.courseDetails()[this.selectedCourseId()] || Object.values(this.courseDetails())[0];
  });

  // Current active assessment info
  currentAssessment = computed(() => {
    const course = this.currentCourse();
    return course.assessments.find((a) => a.id === this.selectedAssessmentId()) || course.assessments[0];
  });

  // Highest score for current assessment
  highestScore = computed(() => {
    const assessment = this.currentAssessment();
    if (!assessment || !assessment.attempts || assessment.attempts.length === 0) return null;
    const scores = assessment.attempts
      .filter((a) => a.score !== undefined && !a.pending)
      .map((a) => a.score as number);
    if (scores.length === 0) return null;
    return Math.max(...scores);
  });

  // Filtered courses in list view
  filteredCourses = computed(() => {
    const tab = this.selectedTab();
    const keyword = this.searchKeyword().toLowerCase().trim();

    return this.courses().filter((course) => {
      const matchTab = tab === 'all' || course.status === tab;
      const matchSearch =
        !keyword ||
        course.name.toLowerCase().includes(keyword) ||
        course.teacher.toLowerCase().includes(keyword);
      return matchTab && matchSearch;
    });
  });

  ngOnDestroy(): void {
    clearTimeout(this.toastTimer);
  }

  setTab(tab: 'all' | 'active' | 'done'): void {
    this.selectedTab.set(tab);
  }

  // Navigation handlers
  showView(view: 'list' | 'course' | 'assessment'): void {
    this.activeView.set(view);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  onSelectCourse(courseId: string): void {
    this.selectedCourseId.set(courseId);
    this.showView('course');
  }

  onSelectAssessment(assessmentId: string): void {
    this.selectedAssessmentId.set(assessmentId);
    this.showView('assessment');
  }

  currentFile: File | null = null;

  // Submit Video Modal handlers
  openSubmitModal(): void {
    this.selectedFileName.set('');
    this.hasVideoSelected.set(false);
    this.currentFile = null;
    this.submitNote.set('');
    this.isSubmitModalOpen.set(true);
  }

  closeSubmitModal(): void {
    this.isSubmitModalOpen.set(false);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      this.currentFile = file;
      this.selectedFileName.set(file.name);
      this.hasVideoSelected.set(true);
    }
  }

  onFileDropped(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
      const file = event.dataTransfer.files[0];
      this.currentFile = file;
      this.selectedFileName.set(file.name);
      this.hasVideoSelected.set(true);
    }
  }

  submitVideo(): void {
    if (!this.hasVideoSelected()) return;
    const fileToUpload = this.currentFile;
    this.closeSubmitModal();

    const courseId = this.selectedCourseId();
    const assessmentId = this.selectedAssessmentId();
    const details = { ...this.courseDetails() };
    const course = details[courseId];
    if (!course) return;

    const now = new Date();
    const dateStr = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()} - ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    const assessmentIndex = course.assessments.findIndex((a) => a.id === assessmentId);
    if (assessmentIndex === -1) return;

    const currentAss = course.assessments[assessmentIndex];
    const attemptNo = (currentAss.attempts?.length || 0) + 1;

    const newAttempt: AssessmentAttempt = {
      attemptNo: attemptNo,
      date: dateStr,
      pending: true
    };

    const updatedAssessments = [...course.assessments];
    updatedAssessments[assessmentIndex] = {
      ...currentAss,
      status: 'pending',
      attempts: [newAttempt, ...(currentAss.attempts || [])]
    };

    details[courseId] = {
      ...course,
      assessments: updatedAssessments
    };
    this.courseDetails.set(details);

    this.showToast('Nộp video thành công! Hệ thống đang xử lý và chấm điểm.');

    if (fileToUpload && assessmentId && assessmentId.length === 24) {
      const formData = new FormData();
      formData.append('video', fileToUpload);
      formData.append('attemptNo', attemptNo.toString());
      this.http.post<ApiResponse<any>>(`${environment.apiUrl}/tasks/${assessmentId}/video-results`, formData).subscribe({
        next: () => {},
        error: () => {}
      });
    }

    // Simulate grading completed after 3.5s
    setTimeout(() => {
      const curDetails = { ...this.courseDetails() };
      const curCourse = curDetails[courseId];
      if (!curCourse) return;

      const curAssIdx = curCourse.assessments.findIndex((a) => a.id === assessmentId);
      if (curAssIdx === -1) return;

      const ass = curCourse.assessments[curAssIdx];
      const completedAttempts = ass.attempts.map((att) => {
        if (att.date === dateStr && att.pending) {
          return {
            ...att,
            pending: false,
            duration: '00:00:18',
            score: 9.0
          };
        }
        return att;
      });

      const updatedList = [...curCourse.assessments];
      updatedList[curAssIdx] = {
        ...ass,
        status: 'graded',
        score: 9.0,
        attempts: completedAttempts
      };

      curDetails[courseId] = {
        ...curCourse,
        assessments: updatedList
      };
      this.courseDetails.set(curDetails);
      this.showToast('Hệ thống đã hoàn tất chấm điểm bài nộp của bạn! Điểm: 9.0');
    }, 3500);
  }

  // Review Modal handlers
  openAttemptReview(attempt: AssessmentAttempt): void {
    this.selectedAttempt.set(attempt);
    this.isReviewModalOpen.set(true);
  }

  closeReviewModal(): void {
    this.isReviewModalOpen.set(false);
    this.selectedAttempt.set(null);
  }

  showToast(msg: string): void {
    this.toastMessage.set(msg);
    this.isToastVisible.set(true);
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => {
      this.isToastVisible.set(false);
    }, 3200);
  }
}
