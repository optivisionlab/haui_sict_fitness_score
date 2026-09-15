export type UserRole = 'student' | 'teacher' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  user_code?: string;
  userCode?: string;
  phone_number?: string;
  phoneNumber?: string;
  user_status?: string;
  userStatus?: string;
  date_of_birth?: string;
  dateOfBirth?: string;
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token?: string;
  accessToken?: string;
  token_type?: string;
  tokenType?: string;
  user?: User;
}

export interface ApiResponse<T> {
  success: boolean;
  code: number;
  message: string;
  data: T;
}
