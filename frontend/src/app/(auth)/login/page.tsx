"use client";

import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { clearError } from "@/features/auth/authSlice";
import { useRouter } from "next/navigation";
import { LoginForm } from "@/components/form/login-form";
import { toast } from "sonner";
import { loginUserThunk } from "@/features/auth/authThunks";
import AnimatedRectangles from "./AnimatedRectangles";

export default function LoginPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { loading, error, user, access_token } = useAppSelector(
    (state) => state.auth,
  );

  const handleSubmit = async (data: { username: string; password: string }) => {
    dispatch(clearError());
    const result = await dispatch(loginUserThunk(data));

    if (loginUserThunk.rejected.match(result)) {
      toast.error(result.payload as string);
    } else {
      toast.success("Đăng nhập thành công!");
    }
  };

  useEffect(() => {
    if (access_token && user) {
      router.replace(`/${user.user_role}`);
    }
  }, [access_token, user, router]);

  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">
            <LoginForm onSubmit={handleSubmit} />
            {loading && (
              <p className="text-sm text-gray-500 mt-2">Đang đăng nhập...</p>
            )}
            {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
          </div>
        </div>
      </div>

      <div className="bg-muted relative hidden lg:block lg:">
        <AnimatedRectangles />
      </div>
    </div>
  );
}
