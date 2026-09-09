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
  LucideClock,
  LucideUploadCloud,
  LucidePlay,
  LucidePhone,
  LucideMail,
  LucideX
} from '@lucide/angular';
import { SearchInputComponent } from '@shared/components';
import {
  Course,
  CourseDetailInfo,
  LessonWeek,
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
    LucideClock,
    LucideUploadCloud,
    LucidePlay,
    LucidePhone,
    LucideMail,
    LucideX,
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
  selectedTaskKey = signal<string>('kt1-pickleball');

  // Accordion collapsed state for weeks (indices)
  collapsedWeeks = signal<Set<number>>(new Set([2]));

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

  // Running Simulation state
  isRunning = signal<boolean>(false);
  runTimerText = signal<string>('00:00');
  runStatusText = signal<string>('');
  currentRunLaps = signal<RunLap[]>([]);
  runSummaryText = signal<string>('');
  private runTimerInterval: any = null;
  private runLapInterval: any = null;
  private runElapsedSec = 0;

  // Base courses list
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
      iconType: 'pickleball'
    },
    {
      id: 'chay',
      name: 'Chạy',
      teacher: 'Vũ Thị Lan',
      startDate: '01/09/2026',
      endDate: '30/10/2026',
      examDate: '05/11/2026',
      progress: 100,
      status: 'done',
      iconType: 'chay'
    }
  ]);

  // Course Details dictionary
  courseDetails: Record<string, CourseDetailInfo> = {
    pickleball: {
      id: 'pickleball',
      title: 'Pickleball',
      teacher: 'Đặng Văn Long',
      dates: '01/09/2026 - 15/11/2026',
      examDate: '20/11/2026',
      progress: 45,
      code: '20261PB0001_TX001',
      desc: 'Học phần trang bị cho sinh viên kỹ thuật cơ bản môn Pickleball: cầm vợt, giao bóng, đỡ bóng, di chuyển trên sân và luật thi đấu. Các bài luyện tập được đánh giá bằng hệ thống AI Tracking Video — sinh viên quay lại động tác và nộp video để hệ thống chấm tự động.',
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
      title: 'Chạy',
      teacher: 'Vũ Thị Lan',
      dates: '01/09/2026 - 30/10/2026',
      examDate: '05/11/2026',
      progress: 100,
      code: '20261TD0002_TX001',
      desc: 'Học phần rèn luyện thể lực nền tảng qua các bài chạy bền và chạy tốc độ, kỹ thuật hít thở và tư thế chạy đúng. Bài luyện tập được đánh giá bằng hệ thống AI Tracking Video qua camera nhận diện.',
      qlhtName: 'Bùi Thu Hà',
      qlhtPhone: '0912 345 678',
      qlhtEmail: 'hatb@onschool.edu.vn',
      thumbClass: 'teal',
      thumbIcon: 'chay',
      students: ['Lê Văn C', 'Phạm Thị D'],
      studentTotal: 28
    }
  };

  // Lesson Weeks by Course
  lessonWeeksByCourse: Record<string, LessonWeek[]> = {
    pickleball: [
      {
        label: 'Tuần 1 (01/09/2026 - 07/09/2026)',
        status: 'done',
        lessons: [
          'Lesson 1: Giới thiệu môn học & luật thi đấu',
          'Lesson 2: Kỹ thuật giao bóng cơ bản'
        ],
        items: [
          { title: 'Giới thiệu môn học Pickleball', type: 'L', typeLabel: 'Lecture/ Lý thuyết' },
          { title: 'Luật thi đấu cơ bản', type: 'L', typeLabel: 'Lecture/ Lý thuyết' },
          { title: 'Hướng dẫn kỹ thuật giao bóng (video mẫu)', type: 'L', typeLabel: 'Lecture/ Lý thuyết' },
          {
            title: 'Lesson 2_Task 1: Luyện tập giao bóng tự do',
            type: 'P',
            typeLabel: 'Practice/ Luyện tập',
            taskKey: 'lesson2-task1'
          },
          {
            title: 'Lesson 2_Task 2: Kiểm tra thường xuyên — Kỹ thuật giao bóng (Lần 1)',
            type: 'P',
            typeLabel: 'Practice/ Luyện tập',
            taskKey: 'kt1-pickleball',
            graded: true,
            score: 8
          }
        ]
      },
      {
        label: 'Tuần 2 (08/09/2026 - 14/09/2026)',
        status: 'active',
        lessons: ['Lesson 3: Kỹ thuật đỡ bóng (dink)'],
        items: [
          { title: 'Giới thiệu kỹ thuật đỡ bóng', type: 'L', typeLabel: 'Lecture/ Lý thuyết' },
          { title: 'Video hướng dẫn dink shot', type: 'L', typeLabel: 'Lecture/ Lý thuyết' },
          {
            title: 'Lesson 3_Task 1: Luyện tập đỡ bóng',
            type: 'P',
            typeLabel: 'Practice/ Luyện tập',
            taskKey: 'lesson3-task1'
          }
        ]
      },
      {
        label: 'Tuần 3 (15/09/2026 - 21/09/2026)',
        status: 'locked',
        lessons: ['Lesson 4: Chiến thuật thi đấu đôi'],
        items: []
      }
    ],
    chay: [
      {
        label: 'Tuần 1 (01/09/2026 - 07/09/2026)',
        status: 'done',
        lessons: ['Lesson 1: Giới thiệu môn học & kỹ thuật chạy cơ bản'],
        items: [
          { title: 'Giới thiệu môn học Chạy', type: 'L', typeLabel: 'Lecture/ Lý thuyết' },
          { title: 'Kỹ thuật chạy bền cơ bản', type: 'L', typeLabel: 'Lecture/ Lý thuyết' },
          {
            title: 'Lesson 1_Task 1: Luyện tập chạy tự do',
            type: 'P',
            typeLabel: 'Practice/ Luyện tập',
            taskKey: 'chay-practice-1'
          },
          {
            title: 'Lesson 1_Task 2: Kiểm tra thường xuyên — Chạy 400m (Lần 1)',
            type: 'P',
            typeLabel: 'Practice/ Luyện tập',
            taskKey: 'chay-test-400m',
            graded: true,
            score: 8
          }
        ]
      }
    ]
  };

  // Reactive tasks state
  tasks = signal<Record<string, TaskDetail>>({
    'kt1-pickleball': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'Lesson 2_Task 2: Kiểm tra thường xuyên — Kỹ thuật giao bóng (Lần 1)',
      gradingMethod: 'Lần cao nhất',
      timeLimit: 'Không giới hạn',
      openTime: 'Không thời hạn',
      closeTime: '20/09/2026 23:59',
      attempts: [
        { date: '15/09/2026 - 14:32:05', duration: '00:00:12', attemptNo: 1, score: 8 }
      ]
    },
    'lesson2-task1': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'Lesson 2_Task 1: Luyện tập giao bóng tự do',
      gradingMethod: 'Không tính điểm (luyện tập tự do)',
      timeLimit: 'Không giới hạn',
      openTime: 'Không thời hạn',
      closeTime: 'Không giới hạn',
      attempts: []
    },
    'lesson3-task1': {
      courseKey: 'pickleball',
      type: 'video',
      title: 'Lesson 3_Task 1: Luyện tập đỡ bóng',
      gradingMethod: 'Không tính điểm (luyện tập tự do)',
      timeLimit: 'Không giới hạn',
      openTime: 'Không thời hạn',
      closeTime: 'Không giới hạn',
      attempts: []
    },
    'chay-test-400m': {
      courseKey: 'chay',
      type: 'run-test',
      title: 'Lesson 1_Task 2: Kiểm tra thường xuyên — Chạy 400m (Lần 1)',
      gradingMethod: 'Lần cao nhất',
      timeLimit: 'Không giới hạn',
      openTime: 'Không thời hạn',
      closeTime: '25/09/2026 23:59',
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
      title: 'Lesson 1_Task 1: Luyện tập chạy tự do',
      gradingMethod: 'Không tính điểm (luyện tập tự do)',
      timeLimit: 'Không giới hạn',
      openTime: 'Không thời hạn',
      closeTime: 'Không giới hạn',
      attempts: [],
      laps: [
        { time: '1:40', speed: '4.0 m/s', distance: '400 m', score: 7.5 },
        { time: '1:42', speed: '3.9 m/s', distance: '800 m', score: 7.8 },
        { time: '1:38', speed: '4.1 m/s', distance: '1200 m', score: 8.0 },
        { time: '1:36', speed: '4.2 m/s', distance: '1600 m', score: 8.2 }
      ]
    }
  });

  // Current active course info
  currentCourse = computed(() => {
    return this.courseDetails[this.selectedCourseId()] || this.courseDetails['pickleball'];
  });

  // Current weeks list
  currentWeeks = computed(() => {
    return this.lessonWeeksByCourse[this.selectedCourseId()] || [];
  });

  // Current task info
  currentTask = computed(() => {
    return this.tasks()[this.selectedTaskKey()];
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

  toggleWeek(index: number): void {
    const set = new Set(this.collapsedWeeks());
    if (set.has(index)) {
      set.delete(index);
    } else {
      set.add(index);
    }
    this.collapsedWeeks.set(set);
  }

  isWeekCollapsed(index: number): boolean {
    return this.collapsedWeeks().has(index);
  }

  onItemClick(item: any): void {
    if (item.taskKey) {
      this.showView('task', item.taskKey);
    } else {
      this.showToast(`Đang mở tài liệu: ${item.title}`);
    }
  }

  getInitials(name: string): string {
    const parts = name.trim().split(' ');
    return parts[parts.length - 1].charAt(0).toUpperCase();
  }

  // --- Modal: Submit Video ---
  openSubmitModal(): void {
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
      attempts: [newAttempt, ...(task.attempts || [])]
    };
    this.tasks.set(updatedTasks);

    this.showToast('Đã nộp video thành công! Hệ thống AI Tracking đang phân tích, kết quả sẽ có sau ít phút.');

    // Simulate AI grading finish in 4 seconds
    setTimeout(() => {
      const curTasks = { ...this.tasks() };
      const curTask = curTasks[taskKey];
      if (curTask && curTask.attempts) {
        const completedAttempts = curTask.attempts.map((att) => {
          if (att.date === dateStr && att.pending) {
            return {
              ...att,
              pending: false,
              duration: '00:00:14',
              score: 9.0
            };
          }
          return att;
        });
        curTasks[taskKey] = { ...curTask, attempts: completedAttempts };
        this.tasks.set(curTasks);
      }
    }, 4000);
  }

  // --- Modal: Score Details (AI Tracking) ---
  openScoreModal(): void {
    this.isScoreModalOpen.set(true);
  }

  closeScoreModal(): void {
    this.isScoreModalOpen.set(false);
  }

  // --- Running Simulation (Chạy) ---
  startRun(): void {
    const task = this.currentTask();
    if (!task || !task.laps) return;

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
      this.runStatusText.set('Đang chạy... camera đang theo dõi (kết quả hiển thị theo thời gian thực)');
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
      this.runStatusText.set('Đang chạy... camera đang theo dõi');
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
      const avg = (task.laps.reduce((s, l) => s + l.score, 0) / task.laps.length).toFixed(1);
      this.runSummaryText.set(`Điểm trung bình: ${avg}`);
      this.showToast(`Đã hoàn thành bài chạy! Điểm trung bình: ${avg}`);
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
    }, 3200);
  }
}
