// redux/store.ts
import { configureStore } from "@reduxjs/toolkit";

// Import các slice
import authReducer from "@/features/auth/authSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
  },
});

// Khai báo type cho TypeScript
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
