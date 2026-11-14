import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title?: string;
  message: string;
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  readonly toasts = signal<Toast[]>([]);

  show(options: Omit<Toast, 'id'>): void {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const toast: Toast = {
      id,
      duration: options.duration ?? 4000,
      ...options
    };

    this.toasts.update((current) => [...current, toast]);

    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        this.dismiss(id);
      }, toast.duration);
    }
  }

  success(message: string, title: string = 'Thành công'): void {
    this.show({ type: 'success', title, message });
  }

  error(message: string, title: string = 'Thất bại'): void {
    this.show({ type: 'error', title, message });
  }

  info(message: string, title: string = 'Thông báo'): void {
    this.show({ type: 'info', title, message });
  }

  warning(message: string, title: string = 'Cảnh báo'): void {
    this.show({ type: 'warning', title, message });
  }

  dismiss(id: string): void {
    this.toasts.update((current) => current.filter((t) => t.id !== id));
  }
}
