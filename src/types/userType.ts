// Kiểu thông tin user
export interface UserType {
  user_id: number;
  user_name: string;
  full_name: string;
  email: string;
  user_code: string;
  phone_number: string;
  user_role: string;
  user_status: string;
  date_of_birth: string;
  avatar_url?: string;
}

// Kiểu user lưu trong local
export interface UserLocalType {
  role?: string;
}
