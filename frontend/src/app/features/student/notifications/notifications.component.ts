import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideGraduationCap,
  LucideAlertCircle,
  LucideInfo,
  LucideCheckCheck,
  LucideTrash2,
  LucideCheck
} from '@lucide/angular';
import { NotificationService } from '@core/services/notification.service';
import { NotificationItem } from '@core/models/notification.model';
import { SearchInputComponent, PaginationComponent } from '@shared/components';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [
    CommonModule,
    LucideGraduationCap,
    LucideAlertCircle,
    LucideInfo,
    LucideCheckCheck,
    LucideTrash2,
    LucideCheck,
    SearchInputComponent,
    PaginationComponent
  ],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.scss'
})
export class NotificationsComponent {
  notificationService = inject(NotificationService);
  private router = inject(Router);

  // Tabs: 'all' | 'unread' | 'course' | 'exam' | 'system'
  selectedTab = signal<'all' | 'unread' | 'course' | 'exam' | 'system'>('all');
  searchKeyword = signal<string>('');

  // Pagination
  currentPage = signal<number>(1);
  pageSize = signal<number>(5);

  filteredNotifications = computed(() => {
    const tab = this.selectedTab();
    const keyword = this.searchKeyword().toLowerCase().trim();
    const list = this.notificationService.notifications();

    return list.filter((item) => {
      // Tab filter
      let matchTab = true;
      if (tab === 'unread') matchTab = !item.read;
      else if (tab === 'course') matchTab = item.type === 'course';
      else if (tab === 'exam') matchTab = item.type === 'exam';
      else if (tab === 'system') matchTab = item.type === 'system';

      // Search keyword filter
      const matchSearch =
        !keyword ||
        item.title.toLowerCase().includes(keyword) ||
        item.message.toLowerCase().includes(keyword) ||
        (item.sender && item.sender.toLowerCase().includes(keyword));

      return matchTab && matchSearch;
    });
  });

  paginatedNotifications = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredNotifications().slice(start, start + this.pageSize());
  });

  setTab(tab: 'all' | 'unread' | 'course' | 'exam' | 'system'): void {
    this.selectedTab.set(tab);
    this.currentPage.set(1);
  }

  onNotificationClick(item: NotificationItem): void {
    this.notificationService.markAsRead(item.id);
    if (item.link) {
      this.router.navigateByUrl(item.link);
    }
  }

  markAsRead(event: MouseEvent, item: NotificationItem): void {
    event.stopPropagation();
    this.notificationService.markAsRead(item.id);
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead();
  }

  deleteNotification(event: MouseEvent, item: NotificationItem): void {
    event.stopPropagation();
    this.notificationService.deleteNotification(item.id);
  }

  setPage(page: number): void {
    this.currentPage.set(page);
  }
}
