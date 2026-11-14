import { Routes } from '@angular/router';
import { MainLayoutComponent } from './layouts/main-layout/main-layout.component';
import { authGuard, noAuthGuard, roleGuard } from './core/guards/auth.guard';

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
    canActivate: [noAuthGuard],
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
    canActivate: [authGuard, roleGuard],
    data: { roles: ['student'] },
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
        path: 'courses/:id',
        loadComponent: () =>
          import('./features/student/courses/courses.component').then(
            (m) => m.CoursesComponent
          )
      },
      {
        path: 'courses/:id/assessment/:assessmentId',
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
    path: 'teacher',
    component: MainLayoutComponent,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['teacher', 'admin'] },
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'classes'
      },
      {
        path: 'classes',
        loadComponent: () =>
          import('./features/teacher/classes/teacher-classes.component').then(
            (m) => m.TeacherClassesComponent
          )
      },
      {
        path: 'classes/:id',
        loadComponent: () =>
          import('./features/teacher/class-detail/teacher-class-detail.component').then(
            (m) => m.TeacherClassDetailComponent
          )
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./features/teacher/notifications/teacher-notifications.component').then(
            (m) => m.TeacherNotificationsComponent
          )
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./features/teacher/profile/teacher-profile.component').then(
            (m) => m.TeacherProfileComponent
          )
      }
    ]
  },
  {
    path: 'admin',
    component: MainLayoutComponent,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['admin'] },
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'dashboard'
      },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/admin/dashboard/admin-dashboard.component').then(
            (m) => m.AdminDashboardComponent
          )
      },
      {
        path: 'users',
        loadComponent: () =>
          import('./features/admin/users/admin-users.component').then(
            (m) => m.AdminUsersComponent
          )
      },
      {
        path: 'sports',
        loadComponent: () =>
          import('./features/admin/sports/admin-sports.component').then(
            (m) => m.AdminSportsComponent
          )
      },
      {
        path: 'classes',
        loadComponent: () =>
          import('./features/admin/classes/admin-classes.component').then(
            (m) => m.AdminClassesComponent
          )
      },
      {
        path: 'classes/:id',
        loadComponent: () =>
          import('./features/admin/classes/class-detail/admin-class-detail.component').then(
            (m) => m.AdminClassDetailComponent
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
