import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/auth.model';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated() || authService.getToken()) {
    return true;
  }

  return router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url }
  });
};

export const roleGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const expectedRoles = (route.data?.['roles'] as UserRole[]) || [];
  const currentRole = authService.userRole();

  if (expectedRoles.length === 0 || (currentRole && expectedRoles.includes(currentRole))) {
    return true;
  }

  if (currentRole === 'admin') {
    return true;
  }

  if (currentRole === 'student') {
    return router.createUrlTree(['/student/home']);
  } else if (currentRole === 'teacher') {
    return router.createUrlTree(['/teacher/classes']);
  }

  return router.createUrlTree(['/login']);
};

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
