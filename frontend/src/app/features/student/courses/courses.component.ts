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
import {
  Course,
  CourseDetailInfo,
  AssessmentItem,
  AssessmentAttempt,
  CourseGradesSummary
} from './models/course-detail.model';

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
  submitType = signal<'practice' | 'exam'>('practice');
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
            const isBadminton =
              courseName.toLowerCase().includes('cầu lông') ||
              courseName.toLowerCase().includes('badminton') ||
              courseName.toLowerCase().includes('pickleball');
            const classCode = e.courseCode || e.code || (courseId.length > 8 ? courseId.substring(0, 10).toUpperCase() : courseId);
            const avg = e.grades?.finalScore ?? e.grades?.processScore ?? e.grades?.attendanceScore ?? null;

            // Xử lý tóm tắt điểm
            const grades = e.grades || {};
            const taskScores = e.taskScores || e.task_scores || {};
            const kt1 = taskScores['tx1'] ?? taskScores['task-0'] ?? (e.grades?.processScore ? e.grades.processScore : undefined);
            const kt2 = taskScores['tx2'] ?? taskScores['task-1'] ?? undefined;
            const hasAny = (
              (grades.finalScore !== null && grades.finalScore !== undefined) ||
              (grades.processScore !== null && grades.processScore !== undefined) ||
              (grades.examScore !== null && grades.examScore !== undefined) ||
              (grades.attendanceScore !== null && grades.attendanceScore !== undefined) ||
              kt1 !== undefined ||
              kt2 !== undefined ||
              Object.keys(taskScores).length > 0
            );
            const gradesSummary: CourseGradesSummary = {
              attendanceScore: grades.attendanceScore ?? undefined,
              processScore: grades.processScore ?? undefined,
              examScore: grades.examScore ?? undefined,
              finalScore: grades.finalScore ?? undefined,
              kt1Score: kt1 !== undefined ? Number(kt1) : undefined,
              kt2Score: kt2 !== undefined ? Number(kt2) : undefined,
              hasAnyGrade: hasAny
            };

            return {
              id: courseId,
              name: courseName,
              code: classCode,
              teacher: e.teacherName || 'Giảng viên phụ trách',
              startDate: '01/09/2026',
              endDate: '15/12/2026',
              examDate: this.formatDate(e.examDate),
              progress: Math.round(e.progressPercent || 0),
              status: 'active',
              iconType: isBadminton ? 'pickleball' : 'chay',
              averageScore: avg !== null ? avg : undefined,
              gradesSummary
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
              code: c.code,
              desc: 'Học phần giáo dục thể chất đào tạo kỹ thuật chuyên môn và rèn luyện thể lực. Chấm điểm và đánh giá tự động qua video bằng AI.',
              thumbClass: '',
              thumbIcon: c.iconType,
              averageScore: c.averageScore,
              gradesSummary: c.gradesSummary,
              assessments: []
            };
            this.loadCourseAssessments(c.id);
          });
          this.courseDetails.set(detailsMap);
        } else {
          this.courses.set([]);
          this.courseDetails.set({});
        }
      },
      error: () => {
        this.courses.set([]);
        this.courseDetails.set({});
      }
    });
  }

  private loadCourseAssessments(courseId: string): void {
    if (!courseId) return;
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/student/courses/${courseId}/grades`).subscribe({
      next: (res) => {
        const data = res?.data;
        if (!data || !data.tasks || data.tasks.length === 0) return;

        const mappedAssessments: AssessmentItem[] = data.tasks.map((t: any, idx: number) => {
          const isExam = t.category === 'exam' || idx === data.tasks.length - 1;
          const type = isExam ? 'final' : (idx === 0 ? 'tx1' : 'tx2');
          const hasScore = t.score !== null && t.score !== undefined;

          let formattedName = t.taskTitle || '';
          let guidelines = '';
          if (idx === 0) {
            formattedName = formattedName.includes('KT1') ? formattedName : `KT1: Kỹ thuật 1 - ${formattedName || 'Giao bóng & Cầm vợt chuẩn'}`;
            guidelines = 'Yêu cầu kỹ thuật: Tư thế chuẩn bị cân bằng, trọng tâm hạ thấp. Góc tiếp xúc bóng chính xác ở điểm rơi trước người. Thực hiện vung vợt mượt mà và kết thúc động tác qua vai đối diện.';
          } else if (idx === 1 && !isExam) {
            formattedName = formattedName.includes('KT2') ? formattedName : `KT2: Kỹ thuật 2 - ${formattedName || 'Di chuyển & Đỡ bóng (Dink shot)'}`;
            guidelines = 'Yêu cầu kỹ thuật: Di chuyển nhanh nhẹn bằng bước đệm, giữ mặt vợt ổn định khi tiếp xúc bóng. Kiểm soát lực đánh bóng vừa phải, đảm bảo bóng qua lưới an toàn rơi vào khu vực quy định.';
          } else if (isExam) {
            formattedName = formattedName.includes('Thi') ? formattedName : `Thi: Nộp bài thi kết thúc học phần`;
            guidelines = 'Yêu cầu bài thi: Thực hiện chuỗi kỹ thuật tổng hợp trong vòng 2-3 phút theo quy chuẩn thi đấu. Camera ghi hình toàn thân rõ nét từ đầu đến chân. Bài thi chỉ được nộp 1 lần duy nhất.';
          } else {
            formattedName = `KT${idx + 1}: Kỹ thuật ${idx + 1} - ${formattedName}`;
            guidelines = 'Thực hiện động tác chuẩn xác theo hướng dẫn của giảng viên. Ghi hình đủ góc nhìn toàn thân.';
          }

          const existingAttempt: AssessmentAttempt[] = hasScore
            ? [
                {
                  attemptNo: 1,
                  date: t.submittedAt ? new Date(t.submittedAt).toLocaleString('vi-VN') : 'Đã hoàn thành',
                  duration: '0:45',
                  score: t.score,
                  isExamSubmission: isExam
                }
              ]
            : [];

          return {
            id: t.taskId || `task-${idx}`,
            name: formattedName,
            type: type as any,
            category: isExam ? 'exam' : 'practice',
            gradingMethod: isExam ? 'Lần duy nhất' : 'Lần cao nhất',
            timeLimit: isExam ? '60 phút' : 'Không giới hạn',
            openTime: '01/09/2026 08:00',
            closeTime: '20/11/2026 23:59',
            status: hasScore ? 'graded' : (t.status === 'pending' ? 'pending' : 'not_submitted'),
            score: hasScore ? t.score : undefined,
            aiPredictedScore: hasScore ? t.score : undefined,
            guidelines,
            maxAttempts: isExam ? 1 : undefined,
            attempts: existingAttempt,
            practiceAttempts: isExam ? [] : existingAttempt,
            examAttempt: isExam && hasScore ? existingAttempt[0] : null,
            isExamSubmitted: isExam && hasScore
          };
        });

        this.courseDetails.update((prev) => {
          const existing = prev[courseId] || {
            id: courseId,
            title: data.courseName || 'Pickleball',
            teacher: data.teacherName || 'ThS. Đặng Văn Long',
            dates: '01/09/2026 - 15/11/2026',
            examDate: '20/11/2026',
            progress: 0,
            code: courseId.length > 8 ? courseId.substring(0, 10).toUpperCase() : courseId,
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
          this.videoResultService.getVideoResults({ student_id: studentId }).subscribe({
            next: (vrRes) => {
              const videoList = vrRes?.data || [];
              if (videoList.length > 0) {
                this.courseDetails.update((prev) => {
                  const currCourse = prev[courseId];
                  if (!currCourse) return prev;
                  const updatedAssessments = currCourse.assessments.map((ass) => {
                    const matchingVideos = videoList.filter(
                      (v) => v.exercise_id === ass.id && (!v.course_id || v.course_id === courseId)
                    );
                    if (matchingVideos.length > 0) {
                      const videoAttempts: AssessmentAttempt[] = matchingVideos.map((v, i) => ({
                        attemptNo: matchingVideos.length - i,
                        date: new Date(v.created_at).toLocaleString('vi-VN'),
                        pending: v.status === 'pending' || v.status === 'processing',
                        score: v.score !== null && v.score !== undefined ? v.score : undefined,
                        videoUrl: v.video_url,
                        videoResultId: v.id,
                        isExamSubmission: ass.category === 'exam' || i === 0
                      }));
                      const isPending = matchingVideos.some((v) => v.status === 'pending' || v.status === 'processing');
                      const latestScore = matchingVideos.find(v => v.score !== null && v.score !== undefined)?.score;

                      const examAtt = ass.category === 'exam'
                        ? (videoAttempts.length > 0 ? videoAttempts[0] : null)
                        : (videoAttempts.find(a => a.isExamSubmission) || null);
                      const isExamSub = !!examAtt || (ass.category === 'exam' && videoAttempts.length > 0);

                      return {
                        ...ass,
                        status: isPending ? ('pending' as const) : ass.status,
                        attempts: videoAttempts,
                        practiceAttempts: ass.category === 'exam' ? [] : videoAttempts.filter(a => !a.isExamSubmission),
                        examAttempt: examAtt,
                        isExamSubmitted: isExamSub,
                        aiPredictedScore: latestScore ?? ass.score ?? ass.aiPredictedScore
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
    id: 'tx1',
    name: 'Bài kiểm tra',
    type: 'tx1',
    category: 'exam',
    gradingMethod: 'Lần cao nhất',
    timeLimit: 'Không giới hạn',
    openTime: '01/09/2026',
    closeTime: '30/10/2026',
    status: 'not_submitted',
    attempts: []
  };

  // Current active assessment info
  currentAssessment = computed<AssessmentItem>(() => {
    const course = this.currentCourse();
    if (!course || !course.assessments || course.assessments.length === 0) return this.defaultAssessment;
    return course.assessments.find((a: AssessmentItem) => a.id === this.selectedAssessmentId()) || course.assessments[0] || this.defaultAssessment;
  });

  // Highest score for current assessment
  highestScore = computed<number | null>(() => {
    const assessment = this.currentAssessment();
    if (!assessment || !assessment.attempts || assessment.attempts.length === 0) return null;
    const scores = assessment.attempts
      .filter((a: AssessmentAttempt) => a.score !== undefined && !a.pending)
      .map((a: AssessmentAttempt) => a.score as number);
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
  openSubmitModal(type: 'practice' | 'exam' = 'practice'): void {
    const assessment = this.currentAssessment();
    if (type === 'exam' && assessment.isExamSubmitted) {
      this.showToast('Bài kiểm tra chính thức chỉ được nộp 1 lần duy nhất và bạn đã hoàn thành nộp bài!');
      return;
    }
    this.submitType.set(type);
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
    const user = this.authService.currentUser();
    const studentId = user?.id || user?.user_code || '67890';
    const isExam = this.submitType() === 'exam';

    this.isUploading.set(true);
    this.uploadProgress.set(0);

    this.videoResultService.uploadVideo({
      file,
      student_id: studentId,
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
                attemptNo: attemptNo,
                date: dateStr,
                pending: true,
                videoUrl: videoResult?.video_url,
                videoResultId: videoResult?.id,
                isExamSubmission: isExam
              };

              const updatedPractice = isExam
                ? (currentAss.practiceAttempts || [])
                : [newAttempt, ...(currentAss.practiceAttempts || [])];
              const updatedExam = isExam ? newAttempt : (currentAss.examAttempt || null);
              const aiScore = videoResult?.score ?? (isExam ? 8.5 : 8.0);

              const updatedAssessments = [...course.assessments];
              updatedAssessments[assessmentIndex] = {
                ...currentAss,
                status: 'pending',
                attempts: [newAttempt, ...(currentAss.attempts || [])],
                practiceAttempts: updatedPractice,
                examAttempt: updatedExam,
                isExamSubmitted: currentAss.isExamSubmitted || isExam,
                aiPredictedScore: currentAss.aiPredictedScore ?? aiScore
              };

              details[courseId] = {
                ...course,
                assessments: updatedAssessments
              };
              this.courseDetails.set(details);
            }
          }

          this.closeSubmitModal();
          this.showToast(
            isExam
              ? 'Nộp video bài kiểm tra thành công! Hệ thống AI đang phân tích và chấm điểm dự kiến bài thi của bạn.'
              : 'Nộp video luyện tập thành công! Bạn có thể xem lại kết quả phân tích động tác của AI.'
          );
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
          if (res?.data?.video_url) {
            this.selectedAttempt.update(curr => curr ? { ...curr, videoUrl: res.data.video_url } : null);
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
