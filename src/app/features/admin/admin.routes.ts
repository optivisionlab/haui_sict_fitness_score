import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'dashboard'
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./dashboard/admin-dashboard.component').then(
        (m) => m.AdminDashboardComponent
      )
  },
  {
    path: 'students',
    loadComponent: () =>
      import('./students/admin-students.component').then(
        (m) => m.AdminStudentsComponent
      )
  },
  {
    path: 'courses',
    loadComponent: () =>
      import('./courses/admin-courses.component').then(
        (m) => m.AdminCoursesComponent
      )
  }
];
