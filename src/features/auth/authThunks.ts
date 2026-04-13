import { createAsyncThunk } from "@reduxjs/toolkit";

export const loginUserThunk = createAsyncThunk(
  "auth/login",
  async (
    credentials: { username: string; password: string },
    { rejectWithValue }
  ) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/user/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        return rejectWithValue(error.message || "Đăng nhập thất bại");
      }

      const data = await res.json();
      const access_token = data.access_token;
      sessionStorage.setItem("access_token", access_token);

      const userRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/user/me`,
        {
          method: "GET",
          headers: { Authorization: `Bearer ${access_token}` },
        }
      );

      const userData = await userRes.json();
      sessionStorage.setItem("user", JSON.stringify(userData));

      return { access_token, user: userData };
    } catch (err: unknown) {
      const error = err instanceof Error ? err.message : "Đăng nhập thất bại";
      return rejectWithValue(error);
    }
  }
);

export const logoutThunk = createAsyncThunk("auth/logout", async () => {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("user");
});
