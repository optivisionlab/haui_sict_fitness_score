import { Component, signal, computed, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideDumbbell,
  LucideFootprints,
  LucideUser,
  LucideChevronDown,
  LucideCheckCircle2,
  LucideLock,
  LucideList,
  LucideUploadCloud,
  LucidePlay,
  LucidePhone,
  LucideMail,
  LucideX,
  LucideAward,
  LucideAlertCircle,
  LucideSparkles,
  LucideShieldCheck,
  LucideRotateCcw
} from '@lucide/angular';
import { SearchInputComponent } from '@shared/components';
import {
  Course,
  CourseDetailInfo,
  ExamBlock,
  TaskDetail,
  RunLap
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
    LucideChevronDown,
    LucideCheckCircle2,
    LucideLock,
    LucideList,
    LucideUploadCloud,
    LucidePlay,
    LucidePhone,
    LucideMail,
    LucideX,
    LucideAward,
    LucideAlertCircle,
    LucideSparkles,
    LucideShieldCheck,
    LucideRotateCcw,
    SearchInputComponent
  ],
  templateUrl: './courses.component.html',
  styleUrl: './courses.component.scss'
})
export class CoursesComponent implements OnDestroy {
  // Navigation views: 'list' | 'detail' | 'lessons' | 'task'
  activeView = signal<'list' | 'detail' | 'lessons' | 'task'>('list');

  // List filter state
  selectedTab = signal<'all' | 'active' | 'done'>('all');
  searchKeyword = signal<string>('');

  // Active course and task keys
  selectedCourseId = signal<string>('pickleball');
  selectedTaskKey = signal<string>('pickleball-exam-kt1');

  // Accordion collapsed state for exam blocks
  collapsedExamBlocks = signal<Set<string>>(new Set([]));

  // Modals
  isSubmitModalOpen = signal<boolean>(false);
  isScoreModalOpen = signal<boolean>(false);
  selectedFileName = signal<string>('');
  hasVideoSelected = signal<boolean>(false);
  submitNote = signal<string>('');

  // Toast
  toastMessage = signal<string>('');
  isToastVisible = signal<boolean>(false);
  private toastTimer: any = null;

  // Running Simulation state (Cho môn Chạy)
  isRunning = signal<boolean>(false);
  runTimerText = signal<string>('00:00');
  runStatusText = signal<string>('');
  currentRunLaps = signal<RunLap[]>([]);
  runSummaryText = signal<string>('');
  private runTimerInterval: any = null;
  private runLapInterval: any = null;
  private runElapsedSec = 0;

  // 1. Base courses list (Hiển thị điểm các bài kiểm tra trực tiếp)
  courses = signal<Course[]>([
    {
      id: 'pickleball',
      name: 'Pickleball',
      teacher: 'Đặng Văn Long',
      startDate: '01/09/2026',
      endDate: '15/11/2026',
      examDate: '20/11/2026',
      progress: 45,
      status: 'active',
      iconType: 'pickleball',
      scores: [
        { label: 'KT1 (Giao bóng)', score: 8.0 }
      ]
    },
    {
      id: 'chay',
      name: 'Chạy (Điền kinh)',
      teacher: 'Vũ Thị Lan',
      startDate: '01/09/2026',
      endDate: '30/10/2026',
      examDate: '05/11/2026',
      progress: 100,
      status: 'done',
      iconType: 'chay',
      scores: [
        { label: 'KT1 (Chạy 400m)', score: 8.3 }
      ]
    }
  ]);

  // 2. Course Details dictionary
  courseDetails: Record<string, CourseDetailInfo> = {
    pickleball: {
      id: 'pickleball',
      title: 'Pickleball',
      teacher: 'Đặng Văn Long',
      dates: '01/09/2026 - 15/11/2026',
      examDate: '20/11/2026',
      progress: 45,
      code: '20261PB0001_TX001',
      desc: 'Học phần trang bị cho sinh viên kỹ thuật môn Pickleball: cầm vợt, giao bóng, đỡ bóng (dink shot) và luật thi đấu. Mọi bài kiểm tra và luyện tập đều được phân tích, đánh giá điểm dự kiến bởi công nghệ AI Tracking Video tự động.',
      qlhtName: 'Bùi Thu Hà',
      qlhtPhone: '0912 345 678',
      qlhtEmail: 'hatb@onschool.edu.vn',
      thumbClass: '',
      thumbIcon: 'pickleball',
      students: ['Nguyễn Văn A', 'Trần Thị B', 'Lê Văn C', 'Phạm Thị D'],
      studentTotal: 32
    },
    chay: {
      id: 'chay',
      title: 'Chạy (Điền kinh)',
      teacher: 'Vũ Thị Lan',
      dates: '01/09/2026 - 30/10/2026',
      examDate: '05/11/2026',
      progress: 100,
      code: '20261TD0002_TX001',
      desc: 'Học phần rèn luyện thể lực nền tảng qua các bài chạy cự ly và chạy tốc độ. Đánh giá tự động qua hệ thống camera AI Tracking nhận diện tư thế, vận tốc và quãng đường chạy.',
      qlhtName: 'Bùi Thu Hà',
      qlhtPhone: '0912 345 678',
      qlhtEmail: 'hatb@onschool.edu.vn',
      thumbClass: 'teal',
      thumbIcon: 'chay',
      students: ['Lê Văn C', 'Phạm Thị D'],
      studentTotal: 28
    }
  };

  // 3. Exam Blocks by Course: CHỈ CÓ CÁC BÀI KIỂM TRA + MỤC THI
  examBlocksByCourse = signal<Record<string, ExamBlock[]>>({
    pickleball: [
      {
        id: 'eb-kt1',
        label: 'KT1: Kỹ thuật 1 - Giao bóng cơ bản',
        status: 'done',
        aiEstimatedScore: 8.0,
        practiceItem: {
          id: 'p-kt1',
          title: 'Luyện tập: Kỹ thuật giao bóng tự do',
          taskKey: 'pickleball-practice-kt1',
          requirements: 'Giao bóng dưới thắt lưng, điểm tiếp xúc bóng phía trước thân người, bóng qua lưới vào đúng ô giao bóng đối diện. Tối thiểu 15 lượt.',
          guide: 'Đứng cách vạch cuối sân 30cm, mắt nhìn hướng bóng. Đặt camera quay toàn thân góc nghiêng 45 độ để AI nhận diện góc vung vợt và vị trí thắt lưng.',
          deadline: '20/09/2026 23:59',
          canSubmitMultiple: true,
          submittedCount: 3,
          bestScore: 8.5,
          aiEstimatedScore: 8.5
        },
        examItem: {
          id: 'e-kt1',
          title: 'Nộp bài kiểm tra KT1 (Kỹ thuật giao bóng)',
          taskKey: 'pickleball-exam-kt1',
          deadline: '20/09/2026 23:59',
          canSubmitMultiple: false,
          submitted: true,
          score: 8.0,
          aiEstimatedScore: 8.0
        }
      },
      {
        id: 'eb-kt2',
        label: 'KT2: Kỹ thuật 2 - Đỡ bóng (Dink shot)',
        status: 'active',
        practiceItem: {
          id: 'p-kt2',
          title: 'Luyện tập: Kỹ thuật đỡ bóng mềm sát lưới (Dink shot)',
          taskKey: 'pickleball-practice-kt2',
          requirements: 'Đỡ bóng mềm mại khi bóng vừa nảy khỏi khu vực Non-Volley Zone (Kitchen). Trọng tâm thấp, di chuyển linh hoạt chân trước sau.',
          guide: 'Đứng sát vạch Non-Volley Zone, cổ tay cố định, dùng lực đẩy nhẹ nhàng từ vai và chân để kiểm soát bóng rơi chuẩn trong ô Kitchen đối phương.',
          deadline: '10/10/2026 23:59',
          canSubmitMultiple: true,
          submittedCount: 1,
          bestScore: 7.5,
          aiEstimatedScore: 7.5
        },
        examItem: {
          id: 'e-kt2',
          title: 'Nộp bài kiểm tra KT2 (Kỹ thuật đỡ bóng)',
          taskKey: 'pickleball-exam-kt2',
          deadline: '15/10/2026 23:59',
          canSubmitMultiple: false,
          submitted: false,
          aiEstimatedScore: undefined
        }
      },
      {
        id: 'eb-final',
        label: 'Thi: Nộp bài thi kết thúc học phần',
        isFinalExam: true,
        status: 'active',
        examItem: {
          id: 'e-final',
          title: 'Nộp bài thi kết thúc học phần Pickleball',
          taskKey: 'pickleball-final-exam',
          deadline: '20/11/2026 23:59',
          canSubmitMultiple: false,
          submitted: false,
          isFinalExam: true,
          aiEstimatedScore: undefined
        }
      }
    ],
    chay: [
      {
        id: 'eb-chay-kt1',
        label: 'KT1: Kỹ thuật 1 - Chạy cự ly 400m',
        status: 'done',
        aiEstimatedScore: 8.3,
        practiceItem: {
          id: 'p-chay-kt1',
          title: 'Luyện tập: Kỹ thuật xuất phát cao & Duy trì nhịp thở',
          taskKey: 'chay-practice-1',
          requirements: 'Tư thế xuất phát cao đúng chuẩn, góc nghiêng thân người 15-20 độ, nhịp thở đều đặn và bước chạy ổn định qua các mốc.',
          guide: 'Đặt camera đối diện hoặc nghiêng góc 45 độ để hệ thống AI đo vận tốc tức thời, nhịp bước và gia tốc.',
          deadline: '25/09/2026 23:59',
          canSubmitMultiple: true,
          submittedCount: 4,
          bestScore: 8.2,
          aiEstimatedScore: 8.2
        },
        examItem: {
          id: 'e-chay-kt1',
          title: 'Nộp bài kiểm tra KT1 (Chạy 400m)',
          taskKey: 'chay-test-400m',
          deadline: '25/09/2026 23:59',
          canSubmitMultiple: false,
          submitted: true,
          score: 8.3,
          aiEstimatedScore: 8.3
        }
      },
      {
        id: 'eb-chay-final',
        label: 'Thi: Nộp bài thi kết thúc học phần Chạy',
        isFinalExam: true,
        status: 'active',
        examItem: {
          id: 'e-chay-final',
          title: 'Nộp bài thi kết thúc học phần Điền kinh & Chạy bền',
          taskKey: 'chay-final-exam',
          deadline: '05/11/2026 23:59',
          canSubmitMultiple: false,
          submitted: false,
          isFinalExam: true,
          aiEstimatedScore: undefined
        }
      }
    ]
  });

  // 4. Tasks Detail dictionary
  tasks = signal<Record<string, TaskDetail>>({
    'pickleball-exam-kt1': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'KT1: Kiểm tra Kỹ thuật giao bóng cơ bản (Chính thức)',
      gradingMethod: 'Chấm tự động AI Tracking Video (1 lần duy nhất)',
      timeLimit: 'Không giới hạn thời lượng quay video',
      openTime: '01/09/2026 00:00',
      closeTime: '20/09/2026 23:59',
      canSubmitMultiple: false,
      submitted: true,
      aiEstimatedScore: 8.0,
      requirements: 'Sinh viên quay video thực hiện tối thiểu 20 quả giao bóng liên tục. Đứng đúng vị trí quy định phía sau vạch giao bóng.',
      guide: 'Camera cần cố định, quay rõ toàn bộ cơ thể và sân đấu. Không cắt ghép video. Hệ thống AI sẽ phân tích góc mở cổ tay, độ cao tiếp xúc bóng và quỹ đạo bóng rơi.',
      attempts: [
        {
          date: '15/09/2026 - 14:32:05',
          duration: '00:00:45',
          attemptNo: 1,
          score: 8.0,
          pending: false,
          aiEvaluation: {
            accuracyRate: 90,
            repCount: 20,
            validCount: 18,
            feedback: 'Kỹ thuật giao bóng tốt, tốc độ vung vợt chuẩn xác và ổn định. Chú ý tư thế chuẩn bị chân vững hơn trước khi vung vợt.'
          }
        }
      ]
    },
    'pickleball-practice-kt1': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'Luyện tập KT1: Kỹ thuật giao bóng tự do',
      gradingMethod: 'Đánh giá AI tự động (Luyện tập - Nộp nhiều lần)',
      timeLimit: 'Không giới hạn',
      openTime: '01/09/2026 00:00',
      closeTime: '20/09/2026 23:59',
      canSubmitMultiple: true,
      submitted: false,
      aiEstimatedScore: 8.5,
      requirements: 'Thực hiện các quả giao bóng để làm quen với nhịp và góc tiếp xúc bóng. Bạn có thể nộp nhiều lần để AI chấm và phản hồi hoàn thiện kỹ thuật.',
      guide: 'Nộp video sau mỗi lần luyện tập. AI sẽ chỉ ra lỗi sai về tư thế chân, góc nâng vợt để bạn điều chỉnh trước khi vào bài kiểm tra chính thức.',
      attempts: [
        {
          date: '14/09/2026 - 16:20:10',
          duration: '00:00:38',
          attemptNo: 3,
          score: 8.5,
          pending: false,
          aiEvaluation: {
            accuracyRate: 92,
            repCount: 15,
            validCount: 14,
            feedback: 'Độ nảy của bóng và góc tiếp xúc đã cải thiện rất rõ rệt so với lần 2!'
          }
        },
        {
          date: '12/09/2026 - 09:15:22',
          duration: '00:00:40',
          attemptNo: 2,
          score: 7.8,
          pending: false,
          aiEvaluation: {
            accuracyRate: 80,
            repCount: 15,
            validCount: 12,
            feedback: 'Cần hạ thấp trọng tâm hơn khi chuẩn bị.'
          }
        },
        {
          date: '10/09/2026 - 15:02:18',
          duration: '00:00:35',
          attemptNo: 1,
          score: 7.0,
          pending: false,
          aiEvaluation: {
            accuracyRate: 73,
            repCount: 15,
            validCount: 11,
            feedback: 'Tiếp xúc bóng hơi cao trên thắt lưng, cần hạ vợt thấp hơn.'
          }
        }
      ]
    },
    'pickleball-practice-kt2': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'Luyện tập KT2: Kỹ thuật đỡ bóng mềm (Dink shot)',
      gradingMethod: 'Đánh giá AI tự động (Luyện tập - Nộp nhiều lần)',
      timeLimit: 'Không giới hạn',
      openTime: '21/09/2026 00:00',
      closeTime: '10/10/2026 23:59',
      canSubmitMultiple: true,
      submitted: false,
      aiEstimatedScore: 7.5,
      requirements: 'Quay video đỡ bóng sát vạch Non-Volley Zone tối thiểu 10 lượt.',
      guide: 'Chú ý không bước chân đạp vạch Kitchen khi đánh bóng trên không.',
      attempts: [
        {
          date: '25/09/2026 - 10:11:00',
          duration: '00:00:30',
          attemptNo: 1,
          score: 7.5,
          pending: false,
          aiEvaluation: {
            accuracyRate: 80,
            repCount: 10,
            validCount: 8,
            feedback: 'Cổ tay cần giữ mềm mại hơn khi hãm lực bóng đối phương.'
          }
        }
      ]
    },
    'pickleball-exam-kt2': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'KT2: Kiểm tra Kỹ thuật đỡ bóng Dink shot (Chính thức)',
      gradingMethod: 'Chấm tự động AI Tracking Video (1 lần duy nhất)',
      timeLimit: 'Không giới hạn thời lượng quay video',
      openTime: '21/09/2026 00:00',
      closeTime: '15/10/2026 23:59',
      canSubmitMultiple: false,
      submitted: false,
      aiEstimatedScore: undefined,
      requirements: 'Thực hiện chuỗi 15 quả đỡ bóng dink shot đúng kỹ thuật. Chỉ được nộp 1 lần duy nhất.',
      guide: 'Hãy luyện tập kỹ ở mục Luyện tập trước khi nộp bài kiểm tra chính thức.',
      attempts: []
    },
    'pickleball-final-exam': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'Thi: Nộp bài thi kết thúc học phần môn Pickleball',
      gradingMethod: 'Hệ thống AI chấm điểm dự kiến & Hội đồng duyệt (1 lần duy nhất)',
      timeLimit: 'Video từ 2 - 5 phút',
      openTime: '01/11/2026 00:00',
      closeTime: '20/11/2026 23:59',
      canSubmitMultiple: false,
      submitted: false,
      aiEstimatedScore: undefined,
      requirements: 'Thực hiện bài thi tổng hợp: 10 quả giao bóng + 10 quả dink shot + chuỗi rally phản xạ 10 lượt. CHỈ ĐƯỢC NỘP DUY NHẤT 1 LẦN.',
      guide: 'Video phải liền mạch, thấy rõ khuôn mặt sinh viên ở 5 giây đầu giới thiệu họ tên, mã sinh viên trước khi thực hiện bài thi.',
      attempts: []
    },
    'chay-test-400m': {
      courseKey: 'chay',
      type: 'run-test',
      title: 'KT1: Kiểm tra Chạy 400m (Chính thức)',
      gradingMethod: 'Đo cảm biến camera AI thời gian thực (1 lần duy nhất)',
      timeLimit: '400 mét',
      openTime: '01/09/2026 00:00',
      closeTime: '25/09/2026 23:59',
      canSubmitMultiple: false,
      submitted: true,
      aiEstimatedScore: 8.3,
      requirements: 'Chạy hoàn thành cự ly 400m qua hệ thống camera AI nhận diện tại sân vận động.',
      guide: 'Đeo số báo danh đúng vị trí ngực áo để camera tracking nhận diện chính xác.',
      attempts: [],
      laps: [
        { time: '1:32', speed: '4.3 m/s', distance: '400 m', score: 8.5 },
        { time: '1:35', speed: '4.2 m/s', distance: '800 m', score: 8.2 },
        { time: '1:38', speed: '4.1 m/s', distance: '1200 m', score: 8.0 },
        { time: '1:40', speed: '4.0 m/s', distance: '1600 m', score: 8.3 }
      ]
    },
    'chay-practice-1': {
      courseKey: 'chay',
      type: 'run-practice',
      title: 'Luyện tập KT1: Chạy tự do rèn luyện thể lực',
      gradingMethod: 'Đánh giá AI thời gian thực (Nộp/Chạy nhiều lần)',
      timeLimit: 'Không giới hạn',
      openTime: '01/09/2026 00:00',
      closeTime: 'Không giới hạn',
      canSubmitMultiple: true,
      submitted: false,
      aiEstimatedScore: 8.2,
      requirements: 'Chạy làm quen nhịp độ và nhận kết quả vận tốc, quãng đường từ hệ thống AI.',
      guide: 'Chạy trong làn số 1 hoặc 2 của sân tập có camera AI bao quát.',
      attempts: [],
      laps: [
        { time: '1:40', speed: '4.0 m/s', distance: '400 m', score: 7.5 },
        { time: '1:42', speed: '3.9 m/s', distance: '800 m', score: 7.8 },
        { time: '1:38', speed: '4.1 m/s', distance: '1200 m', score: 8.0 },
        { time: '1:36', speed: '4.2 m/s', distance: '1600 m', score: 8.2 }
      ]
    },
    'chay-final-exam': {
      courseKey: 'chay',
      type: 'run-test',
      title: 'Thi: Nộp bài thi kết thúc học phần Điền kinh',
      gradingMethod: 'Camera AI tự động kết hợp giám khảo (1 lần duy nhất)',
      timeLimit: 'Chạy 1500m',
      openTime: '01/11/2026 00:00',
      closeTime: '05/11/2026 23:59',
      canSubmitMultiple: false,
      submitted: false,
      aiEstimatedScore: undefined,
      requirements: 'Chạy cự ly tiêu chuẩn 1500m tại sân vận động. CHỈ ĐƯỢC CHẠY/NỘP 1 LẦN DUY NHẤT.',
      guide: 'Chuẩn bị trang phục thể thao quy định. Có mặt trước 15 phút để quét mã định danh tại cổng camera AI.',
      attempts: [],
      laps: []
    }
  });

  // Current active course info
  currentCourse = computed(() => {
    return this.courseDetails[this.selectedCourseId()] || this.courseDetails['pickleball'];
  });

  // Current exam blocks list (Chỉ có các bài kiểm tra + thi)
  currentExamBlocks = computed(() => {
    return this.examBlocksByCourse()[this.selectedCourseId()] || [];
  });

  // Current task info
  currentTask = computed(() => {
    return this.tasks()[this.selectedTaskKey()] || this.tasks()['pickleball-exam-kt1'];
  });

  // Highest score for current task attempts
  highestScore = computed(() => {
    const task = this.currentTask();
    if (!task || !task.attempts || task.attempts.length === 0) return 0;
    return task.attempts.reduce((max, a) => (a.score && a.score > max ? a.score : max), 0);
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
    this.stopRunTimers();
    clearTimeout(this.toastTimer);
  }

  setTab(tab: 'all' | 'active' | 'done'): void {
    this.selectedTab.set(tab);
  }

  showView(view: 'list' | 'detail' | 'lessons' | 'task', taskKey?: string): void {
    this.stopRunTimers();
    if (taskKey) {
      this.selectedTaskKey.set(taskKey);
      const t = this.tasks()[taskKey];
      if (t) {
        this.selectedCourseId.set(t.courseKey);
      }
    }
    this.activeView.set(view);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  onStudy(courseId: string): void {
    this.selectedCourseId.set(courseId);
    this.showView('detail');
  }

  toggleExamBlock(blockId: string): void {
    const set = new Set(this.collapsedExamBlocks());
    if (set.has(blockId)) {
      set.delete(blockId);
    } else {
      set.add(blockId);
    }
    this.collapsedExamBlocks.set(set);
  }

  isExamBlockCollapsed(blockId: string): boolean {
    return this.collapsedExamBlocks().has(blockId);
  }

  onOpenTask(taskKey: string): void {
    this.showView('task', taskKey);
  }

  getInitials(name: string): string {
    const parts = name.trim().split(' ');
    return parts[parts.length - 1].charAt(0).toUpperCase();
  }

  // --- Modal: Submit Video ---
  openSubmitModal(): void {
    const task = this.currentTask();
    // Kiểm tra quy định 1 lần duy nhất
    if (task.canSubmitMultiple === false && task.submitted) {
      this.showToast('Bài kiểm tra này chỉ được nộp 1 lần duy nhất và bạn đã hoàn thành!');
      return;
    }

    this.selectedFileName.set('');
    this.hasVideoSelected.set(false);
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
      this.selectedFileName.set(file.name);
      this.hasVideoSelected.set(true);
    }
  }

  onFileDropped(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
      const file = event.dataTransfer.files[0];
      this.selectedFileName.set(file.name);
      this.hasVideoSelected.set(true);
    }
  }

  submitVideo(): void {
    if (!this.hasVideoSelected()) return;
    this.closeSubmitModal();

    const taskKey = this.selectedTaskKey();
    const task = this.tasks()[taskKey];
    if (!task) return;

    const now = new Date();
    const dateStr = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()} - ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    const attemptNo = (task.attempts?.length || 0) + 1;

    // Add pending attempt
    const newAttempt = {
      date: dateStr,
      attemptNo: attemptNo,
      pending: true
    };

    const updatedTasks = { ...this.tasks() };
    updatedTasks[taskKey] = {
      ...task,
      submitted: true, // Đánh dấu đã nộp
      attempts: [newAttempt, ...(task.attempts || [])]
    };
    this.tasks.set(updatedTasks);

    // Cập nhật trạng thái trong examBlocksByCourse
    this.updateExamBlockSubmission(taskKey, undefined);

    this.showToast('Đã nộp video thành công! Hệ thống AI Tracking đang phân tích động tác, điểm dự kiến sẽ có sau ít phút.');

    // Giả lập AI chấm điểm dự kiến sau 3.5 giây
    setTimeout(() => {
      const evaluatedScore = 8.8;
      const curTasks = { ...this.tasks() };
      const curTask = curTasks[taskKey];
      if (curTask && curTask.attempts) {
        const completedAttempts = curTask.attempts.map((att) => {
          if (att.date === dateStr && att.pending) {
            return {
              ...att,
              pending: false,
              duration: '00:00:35',
              score: evaluatedScore,
              aiEvaluation: {
                accuracyRate: 92,
                repCount: 20,
                validCount: 19,
                feedback: 'AI đánh giá: Kỹ thuật tốt, tư thế tiếp xúc bóng đạt chuẩn quy định.'
              }
            };
          }
          return att;
        });

        curTasks[taskKey] = {
          ...curTask,
          aiEstimatedScore: evaluatedScore,
          attempts: completedAttempts
        };
        this.tasks.set(curTasks);

        // Cập nhật điểm AI vào examBlocks và danh sách khóa học
        this.updateExamBlockSubmission(taskKey, evaluatedScore);
        this.showToast(`Hệ thống AI đã hoàn thành đánh giá! Điểm dự kiến của bạn: ${evaluatedScore}/10.`);
      }
    }, 3500);
  }

  private updateExamBlockSubmission(taskKey: string, score?: number): void {
    const courseId = this.selectedCourseId();
    const allBlocks = { ...this.examBlocksByCourse() };
    const courseBlocks = allBlocks[courseId];
    if (!courseBlocks) return;

    const updatedBlocks = courseBlocks.map((block) => {
      if (block.examItem.taskKey === taskKey) {
        return {
          ...block,
          status: 'done' as const,
          aiEstimatedScore: score ?? block.aiEstimatedScore,
          examItem: {
            ...block.examItem,
            submitted: true,
            score: score ?? block.examItem.score,
            aiEstimatedScore: score ?? block.examItem.aiEstimatedScore
          }
        };
      }
      if (block.practiceItem && block.practiceItem.taskKey === taskKey) {
        return {
          ...block,
          practiceItem: {
            ...block.practiceItem,
            submittedCount: block.practiceItem.submittedCount + 1,
            bestScore: score ?? block.practiceItem.bestScore,
            aiEstimatedScore: score ?? block.practiceItem.aiEstimatedScore
          }
        };
      }
      return block;
    });

    allBlocks[courseId] = updatedBlocks;
    this.examBlocksByCourse.set(allBlocks);

    // Đồng bộ điểm lên danh sách khóa học nếu có điểm mới
    if (score) {
      this.courses.update((list) =>
        list.map((c) => {
          if (c.id === courseId) {
            const label = taskKey.includes('kt1') ? 'KT1' : taskKey.includes('kt2') ? 'KT2' : 'Thi';
            const existingScores = c.scores || [];
            const otherScores = existingScores.filter((s) => !s.label.startsWith(label));
            return {
              ...c,
              scores: [...otherScores, { label: `${label}`, score: score }]
            };
          }
          return c;
        })
      );
    }
  }

  // --- Modal: Score Details (AI Tracking) ---
  openScoreModal(): void {
    this.isScoreModalOpen.set(true);
  }

  closeScoreModal(): void {
    this.isScoreModalOpen.set(false);
  }

  // --- Running Simulation (Môn Chạy) ---
  startRun(): void {
    const task = this.currentTask();
    if (!task || !task.laps) return;

    if (task.canSubmitMultiple === false && task.submitted) {
      this.showToast('Bài kiểm tra này chỉ được thực hiện 1 lần duy nhất và bạn đã hoàn thành!');
      return;
    }

    this.isRunning.set(true);
    this.currentRunLaps.set([]);
    this.runSummaryText.set('');
    this.runElapsedSec = 0;
    this.runTimerText.set('00:00');

    this.runTimerInterval = setInterval(() => {
      this.runElapsedSec++;
      const m = Math.floor(this.runElapsedSec / 60);
      const s = this.runElapsedSec % 60;
      this.runTimerText.set(`${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);
    }, 1000);

    if (task.type === 'run-test') {
      this.runStatusText.set('Đang chạy... Camera AI đang theo dõi & phân tích vận tốc thời gian thực');
      let lapIdx = 0;
      this.runLapInterval = setInterval(() => {
        if (lapIdx >= task.laps!.length) {
          clearInterval(this.runLapInterval);
          this.finishRun(task);
          return;
        }
        this.currentRunLaps.update((laps) => [...laps, task.laps![lapIdx]]);
        lapIdx++;
      }, 2000);
    } else {
      this.runStatusText.set('Đang chạy luyện tập... Camera AI theo dõi');
      this.runLapInterval = setTimeout(() => {
        this.currentRunLaps.set(task.laps || []);
        this.finishRun(task);
      }, 5000);
    }
  }

  finishRun(task: TaskDetail): void {
    this.stopRunTimers();
    this.isRunning.set(false);
    if (task.laps && task.laps.length > 0) {
      const avg = parseFloat((task.laps.reduce((s, l) => s + l.score, 0) / task.laps.length).toFixed(1));
      this.runSummaryText.set(`Điểm đánh giá AI dự kiến: ${avg}`);
      this.showToast(`Đã hoàn thành! Điểm đánh giá dự kiến từ AI: ${avg}/10`);

      const taskKey = this.selectedTaskKey();
      const curTasks = { ...this.tasks() };
      curTasks[taskKey] = {
        ...task,
        submitted: true,
        aiEstimatedScore: avg
      };
      this.tasks.set(curTasks);
      this.updateExamBlockSubmission(taskKey, avg);
    }
  }

  stopRunTimers(): void {
    clearInterval(this.runTimerInterval);
    clearTimeout(this.runLapInterval);
    this.runTimerInterval = null;
    this.runLapInterval = null;
    this.isRunning.set(false);
  }

  showToast(msg: string): void {
    this.toastMessage.set(msg);
    this.isToastVisible.set(true);
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => {
      this.isToastVisible.set(false);
    }, 3500);
  }
}
