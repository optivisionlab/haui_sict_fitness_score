import {
  Component,
  ElementRef,
  HostListener,
  inject,
  input,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import {
  LucideBell,
  LucideUser,
  LucideCheckCheck,
  LucideGraduationCap,
  LucideAlertCircle,
  LucideInfo,
  LucideChevronRight
} from '@lucide/angular';
import { NotificationService } from '@core/services/notification.service';
import { NotificationItem } from '@core/models/notification.model';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideBell,
    LucideUser,
    LucideCheckCheck,
    LucideGraduationCap,
    LucideAlertCircle,
    LucideInfo,
    LucideChevronRight
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  title = input<string>('Sinh viên Dashboard');
  userName = input<string>('Nguyễn Văn A');
  studentId = input<string>('SV2026001');

  notificationService = inject(NotificationService);
  private router = inject(Router);
  private elementRef = inject(ElementRef);

  isNotificationOpen = signal<boolean>(false);

  toggleNotification(event: MouseEvent): void {
    event.stopPropagation();
    this.isNotificationOpen.update((open) => !open);
  }

  onNotificationClick(item: NotificationItem): void {
    this.notificationService.markAsRead(item.id);
    this.isNotificationOpen.set(false);
    if (item.link) {
      this.router.navigateByUrl(item.link);
    }
  }

  markAllRead(event: MouseEvent): void {
    event.stopPropagation();
    this.notificationService.markAllAsRead();
  }

  viewAllNotifications(): void {
    this.isNotificationOpen.set(false);
    this.router.navigate(['/student/notifications']);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isNotificationOpen.set(false);
    }
  }
}
