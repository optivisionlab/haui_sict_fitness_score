import { Component, ElementRef, ViewChild, signal, computed, OnDestroy, OnInit, inject } from '@angular/core';
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
  LucideArrowLeft,
  LucideVideo
} from '@lucide/angular';
import { SearchInputComponent } from '@shared/components';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/auth.model';
import { AuthService } from '../../../core/services/auth.service';
import { VideoResultService } from '../../../core/services/video-result.service';
import { VideoResult } from '../../../core/models/video-result.model';
import { metricChips, shotEvents } from '../../../core/utils/match-metrics';
import { CourtMarkerComponent } from '../../../shared/components/court-marker/court-marker.component';
import {
  Course,
  CourseDetailInfo,
  AssessmentItem,
  AssessmentAttempt,
  SubmissionMode
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
    CourtMarkerComponent,
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
    LucideVideo
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
  selectedCourseId = signal<string>('');
  loadError = signal(false);
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
  /** Bài đối kháng: 4 góc nửa sân đối phương SV đánh dấu (null = để AI tự ước lượng lưới). */
  courtPoints = signal<number[][] | null>(null);

  readonly metricChips = metricChips;
  readonly shotEvents = shotEvents;
  @ViewChild('reviewVideo') private reviewVideo?: ElementRef<HTMLVideoElement>;

  static readonly TARGET_ZONE_LABELS: Record<string, string> = {
    full: 'cả nửa sân đối phương',
    kitchen: 'vùng cấm vô lê (Kitchen)',
    deep: 'sau vùng cấm vô lê',
    service_left: 'ô giao bóng bên trái',
    service_right: 'ô giao bóng bên phải'
  };

  targetZoneLabel(zone?: string | null): string {
    return CoursesComponent.TARGET_ZONE_LABELS[zone || 'full'] || '';
  }

  /** Xem lại bài đối kháng: tua video gốc tới trước cú đánh 1 giây. */
  seekReview(time: number): void {
    this.reviewShowAnnotated.set(false);
    const video = this.reviewVideo?.nativeElement;
    if (!video) return;
    video.currentTime = Math.max(0, time - 1);
    void video.play().catch(() => undefined);
  }

  /** Bài thường xuyên có 2 phần: luyện tập (AI chấm, không tính điểm) và kiểm tra (tính điểm). */
  activePart = signal<SubmissionMode>('practice');
  /** Phần đang nộp trong modal nộp video. */
  submitMode = signal<SubmissionMode>('test');
  /** Trong modal xem lại: đang xem video AI chấm hay video gốc. */
  reviewShowAnnotated = signal<boolean>(true);

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

    // 2. Tải danh sách khóa học của sinh viên (kèm thông tin lớp học phần từ backend)
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/enrollments/my-courses`).subscribe({
      next: (res) => {
        const items: any[] = res?.data?.items || (Array.isArray(res?.data) ? res.data : []);
        const mappedCourses: Course[] = items.map((e: any) => {
          const courseName = e.courseName || '';
          const isRunning = (e.sportCode || '').toLowerCase().includes('chay') || /chạy|điền kinh/i.test(courseName);
          const g = e.grades || {};
          return {
            id: e.courseId,
            name: courseName,
            code: e.courseCode || '',
            teacher: e.teacherName || '',
            startDate: this.formatDate(e.startDate),
            endDate: this.formatDate(e.endDate),
            examDate: this.formatDate(e.examDate),
            progress: Math.round(e.progressPercent || 0),
            status: e.status === 'done' || e.courseStatus === 'completed' ? 'done' : 'active',
            iconType: isRunning ? 'chay' : 'pickleball',
            averageScore: g.finalScore ?? g.processScore ?? undefined,
            desc: e.courseDesc || ''
          } as Course & { desc: string };
        });
        this.courses.set(mappedCourses);

        const detailsMap: Record<string, CourseDetailInfo> = {};
        mappedCourses.forEach((c: any) => {
          const prev = this.courseDetails()[c.id];
          detailsMap[c.id] = {
            id: c.id,
            title: c.name,
            teacher: c.teacher,
            dates: c.startDate && c.endDate ? `${c.startDate} - ${c.endDate}` : '',
            examDate: c.examDate,
            progress: c.progress,
            code: c.code,
            desc: c.desc,
            thumbClass: '',
            thumbIcon: c.iconType,
            averageScore: c.averageScore,
            grades: c.grades,
            // Giữ danh sách bài nếu loadCourseAssessments đã trả về trước
            assessments: prev?.assessments || []
          };
          if (!prev) this.loadCourseAssessments(c.id);
        });
        this.courseDetails.set(detailsMap);
        this.loadError.set(false);
      },
      error: () => {
        this.courses.set([]);
        this.loadError.set(true);
      }
    });
  }

  private loadCourseAssessments(courseId: string): void {
    if (!courseId) return;
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/student/courses/${courseId}/grades`).subscribe({
      next: (res) => {
        const data = res?.data;
        if (!data || !data.tasks) return;

        const mappedAssessments: AssessmentItem[] = data.tasks.map((t: any, idx: number) => {
          const isExam = t.category === 'exam';
          const titleLower = (t.taskTitle || '').toLowerCase();
          // Loại bài do GV đặt (kind); dữ liệu cũ chưa có kind thì suy ra từ tiêu đề
          const type = t.kind === 'final' ? 'final'
            : t.kind === 'midterm' ? 'midterm'
            : isExam ? (titleLower.includes('giữa') || titleLower.includes('midterm') ? 'midterm' : 'final')
            : (titleLower.includes('tx2') ? 'tx2' : titleLower.includes('tx1') || idx === 0 ? 'tx1' : 'tx2');
          const mode: 'practice' | 'exam' = isExam ? 'exam' : 'practice';
          const groupTitle = isExam
            ? (type === 'midterm' ? 'Thi giữa kỳ' : 'Thi kết thúc học phần')
            : 'Bài thường xuyên';
          const hasScore = t.score !== null && t.score !== undefined;
          return {
            id: t.taskId,
            name: t.taskTitle || '',
            type: type as any,
            mode,
            groupTitle,
            technicalRequirements: t.technicalRequirements || undefined,
            gradingMethod: CoursesComponent.GRADING_LABELS[t.gradingMethod] || '',
            timeLimit: CoursesComponent.formatDuration(t.timeLimit),
            openTime: this.formatDateTime(t.openTime),
            closeTime: this.formatDateTime(t.closeTime),
            instructionVideoUrl: t.instructionVideoUrl || undefined,
            recordingMode: t.recordingMode === 'match' ? 'match' : 'direct',
            targetZone: t.targetZone || undefined,
            status: t.isLocked && !hasScore
              ? 'locked'
              : hasScore ? 'graded' : (t.status === 'pending' ? 'pending' : 'not_submitted'),
            score: hasScore ? t.score : undefined,
            aiScore: hasScore ? t.score : undefined,
            // Lịch sử nộp bài lấy từ /video-results bên dưới, không tự tạo lần nộp giả
            attempts: []
          };
        });

        this.courseDetails.update((prev) => {
          const existing: CourseDetailInfo = prev[courseId] || {
            ...this.defaultCourseDetail,
            id: courseId,
            title: data.courseName || '',
            teacher: data.teacherName || ''
          };
          return {
            ...prev,
            [courseId]: {
              ...existing,
              progress: Math.round(data.progressPercent ?? existing.progress),
              isEligible: data.isEligible !== false,
              minAttendanceScore: data.minAttendanceScore ?? undefined,
              minProcessScore: data.minProcessScore ?? undefined,
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
      videoResultId: v.id,
      mode: v.mode === 'practice' ? 'practice' : 'test',
      teacherGraded: v.finalScore !== null && v.finalScore !== undefined,
      hasAnnotatedVideo: !!v.hasAnnotatedVideo,
      metrics: v.metrics || undefined
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
    title: '',
    teacher: '',
    dates: '',
    examDate: '',
    progress: 0,
    code: '',
    desc: '',
    thumbClass: '',
    thumbIcon: 'pickleball',
    averageScore: undefined,
    assessments: []
  };

  private static readonly GRADING_LABELS: Record<string, string> = {
    highest: 'Lấy điểm cao nhất',
    latest: 'Lấy điểm lần nộp gần nhất',
    average: 'Lấy điểm trung bình'
  };

  /** Giới hạn thời gian (giây) → "1 phút 30 giây"; không có thì "Không giới hạn". */
  private static formatDuration(seconds?: number | null): string {
    if (!seconds) return 'Không giới hạn';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    if (m && s) return `${m} phút ${s} giây`;
    return m ? `${m} phút` : `${s} giây`;
  }

  /** dd/MM/yyyy HH:mm, hoặc chuỗi rỗng nếu không có giá trị. */
  formatDateTime(dateStr?: string): string {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  formatDate(dateStr?: string): string {
    if (!dateStr) return '';
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
    id: '',
    name: '',
    type: 'tx1',
    mode: 'practice',
    groupTitle: '',
    gradingMethod: '',
    timeLimit: '',
    openTime: '',
    closeTime: '',
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

    // Thứ tự: bài thường xuyên -> thi giữa kỳ -> thi kết thúc học phần
    const rank = (g: { items: AssessmentItem[] }) => {
      const t = g.items[0]?.type;
      return t === 'final' ? 2 : t === 'midterm' ? 1 : 0;
    };
    return groups.sort((x, y) => rank(x) - rank(y));
  });

  // Điểm hiển thị: bài thi lấy lần chấm gần nhất (giống backend), bài tập lấy lần cao nhất
  highestScore = computed<number | null>(() => {
    const assessment = this.currentAssessment();
    if (!assessment || !assessment.attempts || assessment.attempts.length === 0) return null;
    // Chỉ bài kiểm tra mới tính điểm; bài luyện tập không ảnh hưởng điểm học phần
    const graded = assessment.attempts.filter(
      (a: AssessmentAttempt) => a.score !== undefined && !a.pending && a.mode !== 'practice'
    );
    if (graded.length === 0) return null;
    if (this.isExam(assessment)) {
      return graded.reduce((latest, a) => (a.attemptNo > latest.attemptNo ? a : latest)).score as number;
    }
    return Math.max(...graded.map((a: AssessmentAttempt) => a.score as number));
  });

  /** Bài thường xuyên (không phải bài thi) có thêm phần luyện tập. */
  hasPracticePart(assessment: AssessmentItem): boolean {
    return !this.isExam(assessment);
  }

  private numberAttempts(list: AssessmentAttempt[]): AssessmentAttempt[] {
    // Danh sách sắp xếp mới nhất trước; đánh số riêng trong từng phần
    return list.map((a, i) => ({ ...a, displayNo: list.length - i }));
  }

  practiceAttempts = computed(() =>
    this.numberAttempts((this.currentAssessment().attempts || []).filter((a) => a.mode === 'practice'))
  );

  testAttempts = computed(() =>
    this.numberAttempts((this.currentAssessment().attempts || []).filter((a) => a.mode !== 'practice'))
  );

  /** Lịch sử nộp của phần đang xem (bài thi chỉ có phần kiểm tra). */
  visibleAttempts = computed(() => {
    const a = this.currentAssessment();
    if (!this.hasPracticePart(a)) return this.testAttempts();
    return this.activePart() === 'practice' ? this.practiceAttempts() : this.testAttempts();
  });

  setActivePart(part: SubmissionMode): void {
    this.activePart.set(part);
  }

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
    this.activePart.set('practice');
    this.router.navigate(['/student/courses', this.selectedCourseId(), 'assessment', assessmentId]);
  }

  // Submit Video Modal handlers
  openSubmitModal(mode: SubmissionMode = 'test'): void {
    this.submitMode.set(this.hasPracticePart(this.currentAssessment()) ? mode : 'test');
    this.courtPoints.set(null);
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

    const mode = this.submitMode();
    const isMatch = this.currentAssessment()?.recordingMode === 'match';
    this.videoResultService.uploadVideo({
      file,
      exercise_id: assessmentId,
      course_id: courseId,
      mode,
      court_points: isMatch ? this.courtPoints() : null
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
                videoResultId: videoResult?.id,
                mode
              };

              const updatedAssessments = [...course.assessments];
              updatedAssessments[assessmentIndex] = {
                ...currentAss,
                // Bài luyện tập không đổi trạng thái chấm điểm của bài
                status: mode === 'practice' ? currentAss.status : 'pending',
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
          this.activePart.set(mode);
          this.showToast(mode === 'practice'
            ? 'Đã nộp video luyện tập. AI đang chấm, kết quả sẽ hiện trong lịch sử luyện tập.'
            : 'Đã nộp video kiểm tra. AI đang chấm điểm.');
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
    this.reviewShowAnnotated.set(!!attempt.hasAnnotatedVideo);
    this.isReviewModalOpen.set(true);

    if (attempt.videoResultId && attempt.hasAnnotatedVideo && !attempt.annotatedVideoUrl) {
      this.videoResultService.getVideoStreamUrl(attempt.videoResultId, true).subscribe({
        next: (res) => {
          if (res?.data?.videoUrl) {
            this.selectedAttempt.update(curr => curr ? { ...curr, annotatedVideoUrl: res.data.videoUrl } : null);
          }
        },
        error: () => this.reviewShowAnnotated.set(false)
      });
    }

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
