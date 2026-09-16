export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  type: 'course' | 'exam' | 'system';
  read: boolean;
  link?: string;
  sender?: string;
}
