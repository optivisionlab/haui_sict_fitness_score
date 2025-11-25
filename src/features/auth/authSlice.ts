import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { loginUserThunk, logoutThunk } from "./authThunks";

interface User {
  user_id: number;
  user_name: string;
  full_name: string;
  email: string;
  phone_number: string;
  user_code: string;
  user_role: string;
  user_status: string;
  date_of_birth?: Date;
  created_at?: Date;
  updated_at?: Date;
}

interface AuthState {
  access_token: string | null;
  user: User | null;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  access_token: null,
  user: null,
  loading: false,
  error: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setCredentials: (
      state,
      action: PayloadAction<{ access_token: string; user: User }>
    ) => {
      state.access_token = action.payload.access_token;
      state.user = action.payload.user;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUserThunk.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        loginUserThunk.fulfilled,
        (
          state,
          action: PayloadAction<{ access_token: string; user: User }>
        ) => {
          state.loading = false;
          state.access_token = action.payload.access_token;
          state.user = action.payload.user;
        }
      )
      .addCase(loginUserThunk.rejected, (state, action) => {
        state.loading = false;
        state.error = (action.payload as string) || "Đăng nhập thất bại";
      })
      .addCase(logoutThunk.fulfilled, (state) => {
        state.access_token = null;
        state.user = null;
        state.error = null;
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("user");
      });
  },
});

export const { clearError, setCredentials } = authSlice.actions;
export default authSlice.reducer;
