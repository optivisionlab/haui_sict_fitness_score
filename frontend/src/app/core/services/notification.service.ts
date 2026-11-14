import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NotificationItem } from '../models/notification.model';
import { environment } from '@env/environment';
import { ApiResponse } from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private http = inject(HttpClient);

  notifications = signal<NotificationItem[]>([]);
  isLoading = signal<boolean>(false);

  unreadCount = computed(() => {
    return this.notifications().filter((n) => !n.read).length;
  });

  constructor() {
    this.loadNotifications();
  }

  loadNotifications(): void {
    this.isLoading.set(true);
    this.http.get<ApiResponse<any>>(`${environment.apiUrl}/notifications`).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        const rawList = res?.data || [];
        const items: any[] = Array.isArray(rawList) ? rawList : (rawList.items || []);
        const mapped: NotificationItem[] = items.map((n: any) => {
          let type: 'course' | 'exam' | 'system' = 'system';
          const t = (n.type || '').toLowerCase();
          if (t.includes('grade') || t.includes('course') || t.includes('submission')) {
            type = 'course';
          } else if (t.includes('exam') || t.includes('test') || t.includes('deadline')) {
            type = 'exam';
          } else {
            type = 'system';
          }

          return {
            id: n.id || '',
            title: n.title || 'Thông báo',
            message: n.message || '',
            time: this.formatRelativeTime(n.createdAt || n.created_at),
            type: type,
            read: !!(n.isRead ?? n.is_read ?? n.read),
            link: n.link || '/student/courses',
            sender: n.sender || 'Hệ thống Đào tạo',
            createdAt: n.createdAt || n.created_at
          };
        });
        this.notifications.set(mapped);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });
  }

  private formatRelativeTime(dateStr?: string): string {
    if (!dateStr) return 'Gần đây';
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return 'Gần đây';
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'Vừa xong';
      if (diffMins < 60) return `${diffMins} phút trước`;
      if (diffHours < 24) return `${diffHours} giờ trước`;
      if (diffDays === 1) return 'Hôm qua';
      if (diffDays < 7) return `${diffDays} ngày trước`;
      return date.toLocaleDateString('vi-VN');
    } catch {
      return 'Gần đây';
    }
  }

  markAsRead(id: string): void {
    this.notifications.update((items) =>
      items.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    this.http.patch(`${environment.apiUrl}/notifications/${id}/read`, {}).subscribe({
      error: () => {}
    });
  }

  markAllAsRead(): void {
    const unread = this.notifications().filter((n) => !n.read);
    this.notifications.update((items) =>
      items.map((n) => ({ ...n, read: true }))
    );
    unread.forEach((n) => {
      this.http.patch(`${environment.apiUrl}/notifications/${n.id}/read`, {}).subscribe({
        error: () => {}
      });
    });
  }

  deleteNotification(id: string): void {
    this.notifications.update((items) => items.filter((n) => n.id !== id));
    this.http.delete(`${environment.apiUrl}/notifications/${id}`).subscribe({
      error: () => {
        this.loadNotifications();
      }
    });
  }
}
