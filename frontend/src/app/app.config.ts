import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { NavigationError, provideRouter, withNavigationErrorHandler } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
import { jwtInterceptor } from './core/interceptors/jwt.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';

const CHUNK_RELOAD_KEY = 'chunk_reload_at';
const CHUNK_ERROR_RE = /dynamically imported module|Importing a module script failed|ChunkLoadError|Failed to fetch/i;

// Sau khi deploy bản mới, trình duyệt còn giữ bản cũ sẽ không tải được chunk của trang.
// Khi đó tải lại hẳn trang tới URL đích (tối đa 1 lần / 30s để tránh vòng lặp).
function reloadOnChunkError(error: NavigationError): void {
  const message = String((error.error as Error)?.message ?? error.error);
  if (!CHUNK_ERROR_RE.test(message)) return;
  try {
    const last = Number(sessionStorage.getItem(CHUNK_RELOAD_KEY) || 0);
    if (Date.now() - last < 30_000) return;
    sessionStorage.setItem(CHUNK_RELOAD_KEY, String(Date.now()));
  } catch {
    // sessionStorage không dùng được: vẫn reload
  }
  window.location.assign(error.url);
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withNavigationErrorHandler(reloadOnChunkError)),
    provideHttpClient(withInterceptors([jwtInterceptor, errorInterceptor]))
  ]
};
