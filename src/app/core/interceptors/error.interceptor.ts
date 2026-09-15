import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Khi token hết hạn hoặc không hợp lệ (401), tự động đăng xuất
      if (error.status === 401 && !req.url.includes('/auth/login')) {
        authService.logout();
      }

      return throwError(() => error);
    })
  );
};
