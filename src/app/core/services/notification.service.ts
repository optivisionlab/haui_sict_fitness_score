import { Injectable, signal, computed } from '@angular/core';
import { NotificationItem } from '../models/notification.model';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  notifications = signal<NotificationItem[]>([
    {
      id: 'notif-1',
      title: 'Đã có kết quả chấm điểm AI Tracking',
      message: 'Bài tập Lesson 2_Task 2 (Kỹ thuật giao bóng Pickleball) của bạn đã được AI chấm đạt 8.0 điểm.',
      time: '10 phút trước',
      type: 'course',
      read: false,
      link: '/student/courses',
      sender: 'Hệ thống AI Tracking'
    },
    {
      id: 'notif-2',
      title: 'Nhắc nhở hạn nộp bài kiểm tra thường xuyên',
      message: 'Môn Pickleball (20261PB0001_TX001) sắp đến hạn nộp bài kiểm tra thường xuyên vào 20/09/2026.',
      time: '2 giờ trước',
      type: 'exam',
      read: false,
      link: '/student/courses',
      sender: 'Giảng viên Đặng Văn Long'
    },
    {
      id: 'notif-3',
      title: 'Lịch thi dự kiến môn Chạy',
      message: 'Lịch thi dự kiến môn Chạy đã được cập nhật vào ngày 05/11/2026. Sinh viên chú ý chuẩn bị.',
      time: 'Hôm qua lúc 14:30',
      type: 'exam',
      read: false,
      link: '/student/courses',
      sender: 'Phòng Đào tạo'
    },
    {
      id: 'notif-4',
      title: 'Bảo trì hệ thống AI Tracking định kỳ',
      message: 'Hệ thống camera và xử lý video AI Tracking sẽ tiến hành bảo trì nâng cấp vào 23:00 ngày 12/09/2026.',
      time: '05/09/2026',
      type: 'system',
      read: true,
      sender: 'Quản trị hệ thống'
    },
    {
      id: 'notif-5',
      title: 'Chào mừng bạn đến với học kỳ mới',
      message: 'Chúc mừng bạn đã đăng ký thành công các học phần Giáo dục thể chất tại OptiVisionLab.',
      time: '01/09/2026',
      type: 'system',
      read: true,
      sender: 'OptiVisionLab'
    }
  ]);

  unreadCount = computed(() => {
    return this.notifications().filter((n) => !n.read).length;
  });

  markAsRead(id: string): void {
    this.notifications.update((items) =>
      items.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }

  markAllAsRead(): void {
    this.notifications.update((items) =>
      items.map((n) => ({ ...n, read: true }))
    );
  }

  deleteNotification(id: string): void {
    this.notifications.update((items) => items.filter((n) => n.id !== id));
  }
}
