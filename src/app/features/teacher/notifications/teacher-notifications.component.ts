import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideBell,
  LucideClock,
  LucideCheckCheck,
  LucideTrash2,
  LucideFileCheck,
  LucideUsers,
  LucideArrowRight
} from '@lucide/angular';
import { SearchInputComponent, PaginationComponent } from '@shared/components';

export interface TeacherNotification {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
  type: 'class' | 'submission' | 'system';
  classCode?: string;
  link?: string;
}

@Component({
  selector: 'app-teacher-notifications',
  standalone: true,
  imports: [
    CommonModule,
    LucideBell,
    LucideClock,
    LucideCheckCheck,
    LucideTrash2,
    LucideFileCheck,
    LucideUsers,
    LucideArrowRight,
    SearchInputComponent,
    PaginationComponent
  ],
  templateUrl: './teacher-notifications.component.html',
  styleUrl: './teacher-notifications.component.scss'
})
export class TeacherNotificationsComponent {
  // Tabs: 'all' | 'unread' | 'class' | 'submission' | 'system'
  selectedTab = signal<'all' | 'unread' | 'class' | 'submission' | 'system'>('all');
  searchKeyword = signal<string>('');

  currentPage = signal<number>(1);
  pageSize = signal<number>(5);

  notifications = signal<TeacherNotification[]>([
    {
      id: 'tn-01',
      title: 'Nhắc nhở hạn chốt điểm Học phần Pickleball (FIT-PB01)',
      message: 'Bộ môn GDTC thông báo: Đề nghị giáo viên rà soát và thực hiện Chốt điểm trước ngày 20/11/2026.',
      time: '10 phút trước',
      read: false,
      type: 'class',
      classCode: 'FIT-PB01',
      link: '/teacher/classes/pickleball-01'
    },
    {
      id: 'tn-02',
      title: 'Hệ thống AI đã hoàn tất chấm video bài kiểm tra TX2',
      message: '38 video nộp bài của sinh viên lớp FIT-PB01 đã được AI phân tích chuyển động và chấm điểm sơ bộ.',
      time: '1 giờ trước',
      read: false,
      type: 'submission',
      classCode: 'FIT-PB01',
      link: '/teacher/classes/pickleball-01'
    },
    {
      id: 'tn-03',
      title: 'Lớp FIT-RUN02: Toàn bộ sinh viên đã nộp bài TX1',
      message: 'Sĩ số 38/38 sinh viên lớp Điền kinh & Chạy cự ly trung bình đã hoàn thành bài thi 100m.',
      time: 'Hôm qua lúc 15:30',
      read: true,
      type: 'submission',
      classCode: 'FIT-RUN02',
      link: '/teacher/classes/chay-ben-02'
    },
    {
      id: 'tn-04',
      title: 'Cập nhật tiêu chuẩn chấm điểm thể chất HaUI 2026',
      message: 'Hội đồng Khoa học Bộ môn GDTC ban hành hướng dẫn mới về góc độ vung vợt và tư thế tiếp xúc bóng Pickleball.',
      time: '2 ngày trước',
      read: true,
      type: 'system'
    },
    {
      id: 'tn-05',
      title: 'Sinh viên Nguyễn Văn An (FIT-PB01) xin nộp lại bài TX1',
      message: 'Sinh viên gửi yêu cầu hỗ trợ xem lại video do góc quay ban đầu bị thiếu sáng.',
      time: '3 ngày trước',
      read: true,
      type: 'submission',
      classCode: 'FIT-PB01',
      link: '/teacher/classes/pickleball-01'
    }
  ]);

  constructor(private router: Router) {}

  filteredNotifications = computed(() => {
    const tab = this.selectedTab();
    const keyword = this.searchKeyword().toLowerCase().trim();
    const list = this.notifications();

    return list.filter(item => {
      let matchTab = true;
      if (tab === 'unread') matchTab = !item.read;
      else if (tab === 'class') matchTab = item.type === 'class';
      else if (tab === 'submission') matchTab = item.type === 'submission';
      else if (tab === 'system') matchTab = item.type === 'system';

      const matchSearch =
        !keyword ||
        item.title.toLowerCase().includes(keyword) ||
        item.message.toLowerCase().includes(keyword) ||
        (item.classCode && item.classCode.toLowerCase().includes(keyword));

      return matchTab && matchSearch;
    });
  });

  paginatedNotifications = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredNotifications().slice(start, start + this.pageSize());
  });

  unreadCount = computed(() => {
    return this.notifications().filter(n => !n.read).length;
  });

  setTab(tab: 'all' | 'unread' | 'class' | 'submission' | 'system'): void {
    this.selectedTab.set(tab);
    this.currentPage.set(1);
  }

  onNotificationClick(item: TeacherNotification): void {
    this.markAsRead(item.id);
    if (item.link) {
      this.router.navigateByUrl(item.link);
    }
  }

  markAsRead(id: string): void {
    this.notifications.update(list =>
      list.map(n => (n.id === id ? { ...n, read: true } : n))
    );
  }

  markAllAsRead(): void {
    this.notifications.update(list => list.map(n => ({ ...n, read: true })));
  }

  deleteNotification(event: MouseEvent, id: string): void {
    event.stopPropagation();
    this.notifications.update(list => list.filter(n => n.id !== id));
  }

  setPage(page: number): void {
    this.currentPage.set(page);
  }
}
