import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/auth.model';

/**
 * Guard bảo vệ các route yêu cầu đăng nhập
 */
export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated() || authService.getToken()) {
    return true;
  }

  // Chưa đăng nhập -> Chuyển về login kèm returnUrl
  return router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url }
  });
};

/**
 * Guard kiểm tra vai trò (Role-Based Access Control)
 */
export const roleGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const expectedRoles = (route.data?.['roles'] as UserRole[]) || [];
  const currentRole = authService.userRole();

  // Nếu không yêu cầu role cụ thể hoặc role hiện tại khớp
  if (expectedRoles.length === 0 || (currentRole && expectedRoles.includes(currentRole))) {
    return true;
  }

  // Nếu là admin, có thể cho phép truy cập cả các phân hệ quản lý
  if (currentRole === 'admin') {
    return true;
  }

  // Không có quyền truy cập -> Chuyển hướng về phân hệ đúng của người dùng
  if (currentRole === 'student') {
    return router.createUrlTree(['/student/home']);
  } else if (currentRole === 'teacher') {
    return router.createUrlTree(['/teacher/classes']);
  }

  return router.createUrlTree(['/login']);
};

/**
 * Guard ngăn người dùng đã đăng nhập truy cập lại trang Login
 */
export const noAuthGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated() || authService.getToken()) {
    const role = authService.userRole();
    if (role === 'teacher' || role === 'admin') {
      return router.createUrlTree(['/teacher/classes']);
    }
    return router.createUrlTree(['/student/home']);
  }

  return true;
};
