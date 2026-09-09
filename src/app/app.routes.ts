import { Routes } from '@angular/router';
import { MainLayoutComponent } from './layouts/main-layout/main-layout.component';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./features/intro/intro.component').then(
        (m) => m.IntroComponent
      )
  },
  {
    path: 'intro',
    redirectTo: ''
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(
        (m) => m.LoginComponent
      )
  },
  {
    path: 'auth/login',
    redirectTo: 'login'
  },
  {
    path: 'student',
    component: MainLayoutComponent,
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'home'
      },
      {
        path: 'home',
        loadComponent: () =>
          import('./features/student/home/home.component').then(
            (m) => m.HomeComponent
          )
      },
      {
        path: 'courses',
        loadComponent: () =>
          import('./features/student/courses/courses.component').then(
            (m) => m.CoursesComponent
          )
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./features/student/notifications/notifications.component').then(
            (m) => m.NotificationsComponent
          )
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./features/student/profile/profile.component').then(
            (m) => m.ProfileComponent
          )
      },
      {
        path: 'grades',
        loadComponent: () =>
          import('./features/student/grades/grades.component').then(
            (m) => m.GradesComponent
          )
      }
    ]
  },
  {
    path: '404',
    loadComponent: () =>
      import('./features/not-found/not-found.component').then(
        (m) => m.NotFoundComponent
      )
  },
  {
    path: '**',
    redirectTo: '404'
  }
];
