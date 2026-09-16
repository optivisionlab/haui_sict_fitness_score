import {
  Component,
  inject,
  computed,
  input
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, NavigationEnd } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs/operators';
import { LucideUser } from '@lucide/angular';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideUser
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  private router = inject(Router);
  private authService = inject(AuthService);

  private currentUrl = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map(e => e.urlAfterRedirects)
    ),
    { initialValue: this.router.url }
  );

  isTeacher = computed(() => {
    return this.currentUrl().startsWith('/teacher');
  });

  title = input<string>('');
  userName = input<string>('');
  studentId = input<string>('');

  displayTitle = computed(() => {
    if (this.title()) return this.title();
    return this.isTeacher() ? 'Cổng Giảng viên' : 'Sinh viên Dashboard';
  });

  displayName = computed(() => {
    if (this.userName()) return this.userName();
    const user = this.authService.currentUser();
    if (user?.name) return user.name;
    return this.isTeacher() ? 'Giảng viên' : 'Sinh viên';
  });

  displayRole = computed(() => {
    if (this.studentId()) return this.studentId();
    const user = this.authService.currentUser();
    const code = user?.userCode || user?.user_code;
    if (code) return code;
    return this.isTeacher() ? 'Giảng viên' : 'Sinh viên';
  });
}
