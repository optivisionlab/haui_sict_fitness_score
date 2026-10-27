import { Component, signal, computed, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpEventType } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
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
import { AuthService } from '../../../core/services/auth.service';
import { VideoResultService } from '../../../core/services/video-result.service';
import { VideoResult } from '../../../core/models/video-result.model';
import {
  Course,
  CourseDetailInfo,
  AssessmentItem,
  AssessmentAttempt
} from './models/course-detail.model';

const STATUS_POLL_INTERVAL_MS = 3000;
const STATUS_POLL_TIMEOUT_MS = 15 * 60 * 1000;

@Component({
  selector: 'app-courses',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SearchInputComponent,
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
  ],
  templateUrl: './courses.component.html',
  styleUrl: './courses.component.scss'
})
export class CoursesComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);
  private videoResultService = inject(VideoResultService);

  // Navigation views: 'list' (danh sách môn) | 'course' (môn học - danh sách bài) | 'assessment' (chi tiết bài nộp)
  activeView = signal<'list' | 'course' | 'assessment'>('list');

  // List filter state
  selectedTab = signal<'all' | 'active' | 'done'>('all');
  searchKeyword = signal<string>('');

  // Selected state
  selectedCourseId = signal<string>('pickleball');
  selectedAssessmentId = signal<string>('');

  // Modals & Upload State
  isSubmitModalOpen = signal<boolean>(false);
  isReviewModalOpen = signal<boolean>(false);
  selectedFile = signal<File | null>(null);
  selectedFileName = signal<string>('');
  hasVideoSelected = signal<boolean>(false);
  isUploading = signal<boolean>(false);
  uploadProgress = signal<number>(0);
  submitNote = signal<string>('');
  selectedAttempt = signal<AssessmentAttempt | null>(null);

  // Toast
  toastMessage = signal<string>('');
  isToastVisible = signal<boolean>(false);
  private toastTimer: any = null;
  private pollTimers = new Map<string, ReturnType<typeof setTimeout>>();

  // Base courses list
  courses = signal<Course[]>([]);

  // Course Details dictionary
  courseDetails = signal<Record<string, CourseDetailInfo>>({});

  ngOnInit(): void {
    // 1. Lắng nghe thay đổi trên URL để cập nhật view tương ứng
    this.route.paramMap.subscribe((params) => {
      const courseId = params.get('id');
      const assessmentId = params.get('assessmentId');

      if (courseId) {
        this.selectedCourseId.set(courseId);
        this.loadCourseAssessments(courseId);

        if (assessmentId) {
          this.selectedAssessmentId.set(assessmentId);
          this.activeView.set('assessment');
        } else {
          this.activeView.set('course');
        }
      } else {
        this.activeView.set('list');
      }
    });

    // 2. Tải danh sách khóa học của sinh viên
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/enrollments/my-courses`).subscribe({
      next: (res) => {
        const items = res?.data?.items || (Array.isArray(res?.data) ? res.data : []);
        if (items.length > 0) {
          const mappedCourses: Course[] = items.map((e: any) => {
            const courseId = e.courseId || e.id || '';
            const courseName = e.courseName || e.name || 'Giáo dục Thể chất';
            const isBadminton = courseName.toLowerCase().includes('cầu lông') || courseName.toLowerCase().includes('badminton') || courseName.toLowerCase().includes('pickleball');
            const avg = e.grades?.finalScore ?? e.grades?.processScore ?? e.grades?.attendanceScore ?? null;
            return {
              id: courseId,
              name: courseName,
              teacher: e.teacherName || 'Giảng viên phụ trách',
              startDate: '01/09/2026',
              endDate: '15/12/2026',
              examDate: this.formatDate(e.examDate),
              progress: Math.round(e.progressPercent || 0),
              status: 'active',
              iconType: isBadminton ? 'pickleball' : 'chay',
              averageScore: avg !== null ? avg : undefined
            };
          });
          this.courses.set(mappedCourses);

          const detailsMap: Record<string, CourseDetailInfo> = {};
          mappedCourses.forEach((c) => {
            detailsMap[c.id] = {
              id: c.id,
              title: c.name,
              teacher: c.teacher,
              dates: `${c.startDate} - ${c.endDate}`,
              examDate: this.formatDate(c.examDate),
              progress: c.progress,
              code: c.code || (c.id || '').substring(0, 10).toUpperCase(),
              desc: 'Học phần giáo dục thể chất đào tạo kỹ thuật chuyên môn và rèn luyện thể lực. Chấm điểm và đánh giá tự động qua video bằng AI.',
              thumbClass: '',
              thumbIcon: c.iconType,
              averageScore: c.averageScore,
              grades: c.grades,
              assessments: this.getStandardAssessments(c.name)
            };
            this.loadCourseAssessments(c.id);
          });
          this.courseDetails.set(detailsMap);
        } else {
          // Dữ liệu mặc định mẫu chuẩn cho sinh viên trải nghiệm
          const defaultC: Course = {
            id: 'c-pickleball',
            name: 'Pickleball - Kỹ thuật cơ bản & Nâng cao',
            code: 'LHP-GDTC204-01',
            teacher: 'ThS. Nguyễn Văn A',
            startDate: '05/09/2026',
            endDate: '25/12/2026',
            examDate: '28/12/2026',
            progress: 70,
            status: 'active',
            iconType: 'pickleball',
            averageScore: 8.5,
            grades: {
              kt1: 8.5,
              kt2: 9.0,
              dqt: 8.8,
              exam: 8.5,
              final: 8.7,
              letterGrade: 'A'
            }
          };
          this.courses.set([defaultC]);
          this.courseDetails.set({
            [defaultC.id]: {
              id: defaultC.id,
              title: defaultC.name,
              teacher: defaultC.teacher,
              dates: '05/09/2026 - 25/12/2026',
              examDate: '28/12/2026',
              progress: 70,
              code: defaultC.code || 'LHP-GDTC204-01',
              desc: 'Học phần trang bị cho sinh viên kỹ thuật cơ bản môn Pickleball. Đánh giá kết quả học tập qua hình thức nộp video thực hành để hệ thống AI chấm điểm.',
              thumbClass: '',
              thumbIcon: 'pickleball',
              averageScore: 8.5,
              grades: defaultC.grades,
              assessments: this.getStandardAssessments(defaultC.name)
            }
          });
        }
      },
      error: () => {
        const defaultC: Course = {
          id: 'c-pickleball',
          name: 'Pickleball - Kỹ thuật cơ bản & Nâng cao',
          code: 'LHP-GDTC204-01',
          teacher: 'ThS. Nguyễn Văn A',
          startDate: '05/09/2026',
          endDate: '25/12/2026',
          examDate: '28/12/2026',
          progress: 70,
          status: 'active',
          iconType: 'pickleball',
          averageScore: 8.5,
          grades: {
            kt1: 8.5,
            kt2: 9.0,
            dqt: 8.8,
            exam: 8.5,
            final: 8.7,
            letterGrade: 'A'
          }
        };
        this.courses.set([defaultC]);
        this.courseDetails.set({
          [defaultC.id]: {
            id: defaultC.id,
            title: defaultC.name,
            teacher: defaultC.teacher,
            dates: '05/09/2026 - 25/12/2026',
            examDate: '28/12/2026',
            progress: 70,
            code: defaultC.code || 'LHP-GDTC204-01',
            desc: 'Học phần trang bị cho sinh viên kỹ thuật cơ bản môn Pickleball. Đánh giá kết quả học tập qua hình thức nộp video thực hành để hệ thống AI chấm điểm.',
            thumbClass: '',
            thumbIcon: 'pickleball',
            averageScore: 8.5,
            grades: defaultC.grades,
            assessments: this.getStandardAssessments(defaultC.name)
          }
        });
      }
    });
  }

  /**
   * Tạo danh mục bài đánh giá chuẩn theo yêu cầu:
   * KT1: Luyện tập & Kiểm tra (đều nộp nhiều lần; kiểm tra lấy điểm lần nộp gần nhất)
   * KT2: Luyện tập & Kiểm tra (đều nộp nhiều lần; kiểm tra lấy điểm lần nộp gần nhất)
   * Thi: Nộp bài thi kết thúc học phần (nộp nhiều lần, lấy điểm lần nộp gần nhất)
   */
  getStandardAssessments(courseName?: string): AssessmentItem[] {
    return [
      {
        id: 'kt1-practice',
        name: 'Luyện tập: Kỹ thuật giao bóng & đánh thuận tay',
        type: 'tx1',
        mode: 'practice',
        groupTitle: 'KT1: Kỹ thuật 1',
        technicalRequirements: 'Yêu cầu tư thế chuẩn bị, xoay hông, tiếp xúc bóng đúng điểm ngọt của vợt và giữ thăng bằng sau khi kết thúc cú đánh.',
        gradingMethod: 'Nộp nhiều lần - Lấy điểm cao nhất',
        timeLimit: 'Không giới hạn thời gian',
        openTime: '05/09/2026 07:00',
        closeTime: '30/11/2026 23:59',
        status: 'graded',
        score: 8.5,
        aiScore: 8.5,
        attempts: [
          {
            attemptNo: 2,
            date: '20/10/2026 15:30',
            duration: '0:48',
            score: 8.5,
            aiScore: 8.5,
            aiFeedback: 'Đánh giá AI: Điểm dự kiến 8.5/10. Tư thế vung vợt đẹp, điểm tiếp xúc bóng chuẩn xác (14/15 lần đạt). Cổ tay linh hoạt.',
            videoUrl: ''
          },
          {
            attemptNo: 1,
            date: '15/10/2026 10:15',
            duration: '0:42',
            score: 7.0,
            aiScore: 7.0,
            aiFeedback: 'Đánh giá AI: Điểm dự kiến 7.0/10. Biên độ vung vợt hơi hẹp, tiếp xúc bóng hơi muộn.',
            videoUrl: ''
          }
        ]
      },
      {
        id: 'kt1-exam',
        name: 'Bài kiểm tra chính thức KT1: Kỹ thuật giao bóng',
        type: 'tx1',
        mode: 'exam',
        groupTitle: 'KT1: Kỹ thuật 1',
        technicalRequirements: 'Kiểm tra chính thức lấy điểm quá trình đợt 1. Video quay rõ góc máy, toàn thân và sân tập.',
        gradingMethod: 'Lần nộp gần nhất',
        timeLimit: '45 phút',
        openTime: '15/10/2026 08:00',
        closeTime: '30/11/2026 23:59',
        status: 'graded',
        score: 8.5,
        aiScore: 8.5,
        attempts: [
          {
            attemptNo: 1,
            date: '21/10/2026 09:00',
            duration: '1:10',
            score: 8.5,
            aiScore: 8.5,
            aiFeedback: 'Đánh giá AI: Điểm dự kiến 8.5/10. Kỹ thuật giao bóng chuẩn 92%, tốc độ và hướng bóng ổn định.',
            videoUrl: ''
          }
        ]
      },
      {
        id: 'kt2-practice',
        name: 'Luyện tập: Kỹ thuật Dink bóng & Volley trên lưới',
        type: 'tx2',
        mode: 'practice',
        groupTitle: 'KT2: Kỹ thuật 2',
        technicalRequirements: 'Yêu cầu giữ chân vững bên ngoài vùng cấm (Kitchen zone), điều khiển lực tay đánh bóng mềm mại sát mép lưới.',
        gradingMethod: 'Nộp nhiều lần - Lấy điểm cao nhất',
        timeLimit: 'Không giới hạn thời gian',
        openTime: '01/10/2026 07:00',
        closeTime: '05/12/2026 23:59',
        status: 'graded',
        score: 9.0,
        aiScore: 9.0,
        attempts: [
          {
            attemptNo: 1,
            date: '22/10/2026 16:45',
            duration: '0:55',
            score: 9.0,
            aiScore: 9.0,
            aiFeedback: 'Đánh giá AI: Điểm dự kiến 9.0/10. Kỹ thuật Dink bóng xuất sắc, kiểm soát bóng mềm mại và độ chuẩn xác 95%.',
            videoUrl: ''
          }
        ]
      },
      {
        id: 'kt2-exam',
        name: 'Bài kiểm tra chính thức KT2: Kỹ thuật Dink & Volley',
        type: 'tx2',
        mode: 'exam',
        groupTitle: 'KT2: Kỹ thuật 2',
        technicalRequirements: 'Bài kiểm tra chính thức KT2. Ghi hình liên tục không cắt ghép.',
        gradingMethod: 'Lần nộp gần nhất',
        timeLimit: '45 phút',
        openTime: '20/10/2026 08:00',
        closeTime: '05/12/2026 23:59',
        status: 'not_submitted',
        attempts: []
      },
      {
        id: 'final-exam',
        name: 'Thi: Nộp bài thi kết thúc học phần',
        type: 'final',
        mode: 'exam',
        groupTitle: 'Thi: Kết thúc học phần',
        technicalRequirements: 'Bài thi thực hành kết thúc học phần môn Giáo dục thể chất. Video thực hiện chuỗi giao bóng và đánh bóng đối kháng kỹ thuật.',
        gradingMethod: 'Lần nộp gần nhất',
        timeLimit: '60 phút',
        openTime: '10/12/2026 08:00',
        closeTime: '28/12/2026 17:00',
        status: 'not_submitted',
        attempts: []
      }
    ];
  }

  private loadCourseAssessments(courseId: string): void {
    if (!courseId) return;
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/student/courses/${courseId}/grades`).subscribe({
      next: (res) => {
        const data = res?.data;
        if (!data || !data.tasks || data.tasks.length === 0) return;

        const mappedAssessments: AssessmentItem[] = data.tasks.map((t: any, idx: number) => {
          const isExam = t.category === 'exam';
          const titleLower = (t.taskTitle || '').toLowerCase();
          const type = isExam
            ? (titleLower.includes('giữa') || titleLower.includes('midterm') ? 'midterm' : 'final')
            : (titleLower.includes('tx1') || idx === 0 ? 'tx1' : 'tx2');
          const mode: 'practice' | 'exam' = isExam ? 'exam' : 'practice';
          const groupTitle = isExam
            ? (titleLower.includes('giữa') ? 'KT1: Kỹ thuật 1' : 'Thi: Kết thúc học phần')
            : (idx === 0 ? 'KT1: Kỹ thuật 1' : 'KT2: Kỹ thuật 2');
          const hasScore = t.score !== null && t.score !== undefined;
          return {
            id: t.taskId || `task-${idx}`,
            name: t.taskTitle || (isExam ? 'Bài cuối kỳ - Thi đấu tính điểm chính thức' : `Bài thường xuyên ${idx + 1}`),
            type: type as any,
            mode,
            groupTitle,
            technicalRequirements: t.technicalRequirements || (mode === 'practice' ? 'Luyện tập kỹ thuật nhiều lần để hoàn thiện động tác.' : 'Bài kiểm tra chính thức - Được nộp lại, hệ thống lấy điểm lần nộp gần nhất.'),
            gradingMethod: isExam ? 'Lần nộp gần nhất' : 'Lần cao nhất',
            timeLimit: isExam ? '60 phút' : 'Không giới hạn',
            openTime: '01/09/2026 08:00',
            closeTime: '20/11/2026 23:59',
            status: hasScore ? 'graded' : (t.status === 'pending' ? 'pending' : 'not_submitted'),
            score: hasScore ? t.score : undefined,
            aiScore: hasScore ? t.score : undefined,
            attempts: hasScore
              ? [
                  {
                    attemptNo: 1,
                    date: t.submittedAt ? new Date(t.submittedAt).toLocaleString('vi-VN') : 'Đã hoàn thành',
                    duration: '0:45',
                    score: t.score,
                    aiScore: t.score
                  }
                ]
              : []
          };
        });

        this.courseDetails.update((prev) => {
          const existing = prev[courseId] || {
            id: courseId,
            title: data.courseName || 'Pickleball',
            teacher: data.teacherName || 'Đặng Văn Long',
            dates: '01/09/2026 - 15/11/2026',
            examDate: '20/11/2026',
            progress: 0,
            code: courseId.substring(0, 10).toUpperCase(),
            desc: 'Học phần trang bị cho sinh viên kỹ thuật cơ bản môn Pickleball. Đánh giá kết quả học tập qua hình thức nộp video thực hành để hệ thống chấm điểm.',
            thumbClass: '',
            thumbIcon: 'pickleball',
            averageScore: undefined,
            assessments: []
          };
          return {
            ...prev,
            [courseId]: {
              ...existing,
              progress: Math.round(data.progressPercent ?? existing.progress),
              averageScore: data.finalScore ?? data.processScore ?? existing.averageScore,
              assessments: mappedAssessments
            }
          };
        });

        if (this.selectedCourseId() === courseId && mappedAssessments.length > 0) {
          const currentId = this.selectedAssessmentId();
          if (!currentId || !mappedAssessments.some((a: AssessmentItem) => a.id === currentId)) {
            this.selectedAssessmentId.set(mappedAssessments[0].id);
          }
        }

        // Fetch real video submissions from backend to populate attempts
        const user = this.authService.currentUser();
        const studentId = user?.id || user?.user_code;
        if (studentId) {
          this.videoResultService.getVideoResults({ student_id: studentId, page_size: 100 }).subscribe({
            next: (vrRes) => {
              const videoList = vrRes?.data?.items || [];
              if (videoList.length > 0) {
                this.courseDetails.update((prev) => {
                  const currCourse = prev[courseId];
                  if (!currCourse) return prev;
                  const updatedAssessments = currCourse.assessments.map((ass) => {
                    const matchingVideos = videoList
                      .filter((v) => v.taskId === ass.id)
                      .sort((x, y) => y.attemptNo - x.attemptNo);
                    if (matchingVideos.length > 0) {
                      const videoAttempts: AssessmentAttempt[] = matchingVideos.map((v) => this.toAttempt(v));
                      const isPending = videoAttempts.some((a) => a.pending);
                      return {
                        ...ass,
                        status: isPending && ass.status !== 'graded' ? ('pending' as const) : ass.status,
                        attempts: videoAttempts
                      };
                    }
                    return ass;
                  });
                  return {
                    ...prev,
                    [courseId]: {
                      ...currCourse,
                      assessments: updatedAssessments
                    }
                  };
                });
              }
            },
            error: () => {}
          });
        }
      },
      error: () => {}
    });
  }

  /** Map một bài nộp từ API sang dòng lịch sử nộp bài. */
  private toAttempt(v: VideoResult): AssessmentAttempt {
    const score = v.finalScore ?? v.aiScore ?? undefined;
    const failed = v.status === 'failed';
    // Dữ liệu cũ có thể thiếu status nhưng đã có điểm => coi là đã chấm
    const pending = !failed && score === undefined && (v.pending || v.status === 'pending' || v.status === 'processing');
    const duration = v.durationSec ? `${Math.floor(v.durationSec / 60)}:${String(v.durationSec % 60).padStart(2, '0')}` : undefined;
    return {
      attemptNo: v.attemptNo,
      date: new Date(v.submittedAt).toLocaleString('vi-VN'),
      duration,
      pending,
      failed,
      error: v.error || undefined,
      score,
      feedback: v.teacherComment || v.aiComment || undefined,
      videoResultId: v.id
    };
  }

  /** Poll trạng thái chấm điểm sau khi upload cho tới khi completed/failed rồi tải lại kết quả. */
  private pollSubmission(resultId: string, courseId: string, startedAt = Date.now()): void {
    if (Date.now() - startedAt > STATUS_POLL_TIMEOUT_MS) return;
    this.pollTimers.set(
      resultId,
      setTimeout(() => {
        this.videoResultService.getSubmissionStatus(resultId).subscribe({
          next: (res) => {
            const st = res?.data;
            if (st?.status === 'completed' || st?.status === 'failed') {
              this.pollTimers.delete(resultId);
              this.loadCourseAssessments(courseId);
              this.showToast(
                st.status === 'completed'
                  ? `Đã có kết quả chấm điểm: ${st.finalScore ?? st.aiScore} điểm.`
                  : `Chấm điểm thất bại (${st.error || 'lỗi không xác định'}). Vui lòng thử nộp lại.`
              );
              return;
            }
            this.pollSubmission(resultId, courseId, startedAt);
          },
          error: () => this.pollSubmission(resultId, courseId, startedAt)
        });
      }, STATUS_POLL_INTERVAL_MS)
    );
  }

  // Fallback course detail if route is loaded before items
  private defaultCourseDetail: CourseDetailInfo = {
    id: '',
    title: 'Đang tải thông tin môn học...',
    teacher: '',
    dates: '',
    examDate: '',
    progress: 0,
    code: '',
    desc: 'Học phần trang bị cho sinh viên kỹ thuật cơ bản môn Pickleball. Đánh giá kết quả học tập qua hình thức nộp video thực hành để hệ thống chấm điểm.',
    thumbClass: '',
    thumbIcon: 'pickleball',
    averageScore: undefined,
    assessments: []
  };

  formatDate(dateStr?: string): string {
    if (!dateStr) return '20/11/2026';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
    } catch {
      return dateStr;
    }
  }

  // Current active course info
  currentCourse = computed(() => {
    return this.courseDetails()[this.selectedCourseId()] || Object.values(this.courseDetails())[0] || this.defaultCourseDetail;
  });

  private defaultAssessment: AssessmentItem = {
    id: 'kt1-practice',
    name: 'Luyện tập kỹ thuật',
    type: 'tx1',
    mode: 'practice',
    groupTitle: 'KT1: Kỹ thuật 1',
    gradingMethod: 'Lần cao nhất',
    timeLimit: 'Không giới hạn',
    openTime: '01/09/2026',
    closeTime: '30/11/2026',
    status: 'not_submitted',
    attempts: []
  };

  // Current active assessment info
  currentAssessment = computed<AssessmentItem>(() => {
    const course = this.currentCourse();
    if (!course || !course.assessments || course.assessments.length === 0) return this.defaultAssessment;
    return course.assessments.find((a: AssessmentItem) => a.id === this.selectedAssessmentId()) || course.assessments[0] || this.defaultAssessment;
  });

  /** Bài kiểm tra chính thức (KT1 / KT2 / Thi). */
  isExam(assessment: AssessmentItem): boolean {
    return assessment.mode === 'exam' || assessment.type === 'midterm' || assessment.type === 'final';
  }

  // Danh sách bài đánh giá gom theo nhóm KT1, KT2, Thi
  groupedAssessments = computed(() => {
    const course = this.currentCourse();
    if (!course || !course.assessments || course.assessments.length === 0) return [];
    const groups: { title: string; items: AssessmentItem[] }[] = [];
    const map = new Map<string, AssessmentItem[]>();

    course.assessments.forEach((item) => {
      const title = item.groupTitle || (item.type === 'final' ? 'Thi: Kết thúc học phần' : item.type === 'tx2' ? 'KT2: Kỹ thuật 2' : 'KT1: Kỹ thuật 1');
      if (!map.has(title)) {
        map.set(title, []);
      }
      map.get(title)!.push(item);
    });

    map.forEach((items, title) => {
      groups.push({ title, items });
    });

    return groups;
  });

  // Điểm hiển thị: bài thi lấy lần chấm gần nhất (giống backend), bài tập lấy lần cao nhất
  highestScore = computed<number | null>(() => {
    const assessment = this.currentAssessment();
    if (!assessment || !assessment.attempts || assessment.attempts.length === 0) return null;
    const graded = assessment.attempts.filter((a: AssessmentAttempt) => a.score !== undefined && !a.pending);
    if (graded.length === 0) return null;
    if (this.isExam(assessment)) {
      return graded.reduce((latest, a) => (a.attemptNo > latest.attemptNo ? a : latest)).score as number;
    }
    return Math.max(...graded.map((a: AssessmentAttempt) => a.score as number));
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
    this.pollTimers.forEach((timer) => clearTimeout(timer));
    this.pollTimers.clear();
  }

  setTab(tab: 'all' | 'active' | 'done'): void {
    this.selectedTab.set(tab);
  }

  // Navigation handlers syncing with browser URL
  showView(view: 'list' | 'course' | 'assessment'): void {
    if (view === 'list') {
      this.router.navigate(['/student/courses']);
    } else if (view === 'course') {
      this.router.navigate(['/student/courses', this.selectedCourseId()]);
    } else if (view === 'assessment') {
      this.router.navigate(['/student/courses', this.selectedCourseId(), 'assessment', this.selectedAssessmentId()]);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  onSelectCourse(courseId: string): void {
    this.selectedCourseId.set(courseId);
    this.router.navigate(['/student/courses', courseId]);
  }

  onSelectAssessment(assessmentId: string): void {
    this.selectedAssessmentId.set(assessmentId);
    this.router.navigate(['/student/courses', this.selectedCourseId(), 'assessment', assessmentId]);
  }

  // Submit Video Modal handlers
  openSubmitModal(): void {
    this.selectedFile.set(null);
    this.selectedFileName.set('');
    this.hasVideoSelected.set(false);
    this.submitNote.set('');
    this.uploadProgress.set(0);
    this.isUploading.set(false);
    this.isSubmitModalOpen.set(true);
  }

  closeSubmitModal(): void {
    if (this.isUploading()) return;
    this.isSubmitModalOpen.set(false);
    this.selectedFile.set(null);
    this.selectedFileName.set('');
    this.hasVideoSelected.set(false);
    this.submitNote.set('');
    this.uploadProgress.set(0);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      this.selectedFile.set(file);
      this.selectedFileName.set(file.name);
      this.hasVideoSelected.set(true);
    }
  }

  onFileDropped(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
      const file = event.dataTransfer.files[0];
      this.selectedFile.set(file);
      this.selectedFileName.set(file.name);
      this.hasVideoSelected.set(true);
    }
  }

  removeSelectedFile(event?: Event): void {
    if (event) event.stopPropagation();
    if (this.isUploading()) return;
    this.selectedFile.set(null);
    this.selectedFileName.set('');
    this.hasVideoSelected.set(false);
  }

  submitVideo(): void {
    const file = this.selectedFile();
    if (!file) return;

    const courseId = this.selectedCourseId();
    const assessmentId = this.selectedAssessmentId();
    this.isUploading.set(true);
    this.uploadProgress.set(0);

    this.videoResultService.uploadVideo({
      file,
      exercise_id: assessmentId,
      course_id: courseId
    }).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          const percentDone = Math.round((100 * event.loaded) / event.total);
          this.uploadProgress.set(percentDone);
        } else if (event.type === HttpEventType.Response) {
          this.isUploading.set(false);
          const videoResult = event.body?.data;
          const now = new Date();
          const dateStr = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()} - ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

          const details = { ...this.courseDetails() };
          const course = details[courseId];
          if (course) {
            const assessmentIndex = course.assessments.findIndex((a: AssessmentItem) => a.id === assessmentId);
            if (assessmentIndex !== -1) {
              const currentAss = course.assessments[assessmentIndex];
              const attemptNo = (currentAss.attempts?.length || 0) + 1;

              const newAttempt: AssessmentAttempt = {
                attemptNo: videoResult?.attemptNo || attemptNo,
                date: dateStr,
                pending: true,
                videoResultId: videoResult?.id
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
            }
          }

          this.closeSubmitModal();
          this.showToast('Nộp video thành công! Video đã lưu trữ trên MinIO và đang chờ hệ thống AI xử lý.');
          if (videoResult?.id) {
            this.pollSubmission(videoResult.id, courseId);
          }
        }
      },
      error: (err) => {
        this.isUploading.set(false);
        const msg = err?.error?.detail || err?.error?.message || 'Có lỗi xảy ra khi tải video lên server. Vui lòng thử lại.';
        this.showToast(msg);
      }
    });
  }

  // Review Modal handlers
  openAttemptReview(attempt: AssessmentAttempt): void {
    this.selectedAttempt.set(attempt);
    this.isReviewModalOpen.set(true);

    if (attempt.videoResultId && !attempt.videoUrl) {
      this.videoResultService.getVideoStreamUrl(attempt.videoResultId).subscribe({
        next: (res) => {
          if (res?.data?.videoUrl) {
            this.selectedAttempt.update(curr => curr ? { ...curr, videoUrl: res.data.videoUrl } : null);
          }
        },
        error: () => {}
      });
    }
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
