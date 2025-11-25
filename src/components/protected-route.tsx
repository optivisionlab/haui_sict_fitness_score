"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import { setCredentials } from "@/features/auth/authSlice";

interface ProtectedRouteProps {
  allowedRoles: string[];
  children: React.ReactNode;
}

export default function ProtectedRoute({
  allowedRoles,
  children,
}: ProtectedRouteProps) {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { user, access_token } = useAppSelector((state) => state.auth);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // 1. Kiểm tra sessionStorage trước
    const storedToken = sessionStorage.getItem("access_token");
    const storedUser = sessionStorage.getItem("user");

    if (!user && storedToken && storedUser) {
      dispatch(
        setCredentials({
          access_token: storedToken,
          user: JSON.parse(storedUser),
        })
      );
    }

    // 2. Kiểm tra quyền khi có user
    if (user || storedUser) {
      const currentUser = user || JSON.parse(storedUser!);
      if (!allowedRoles.includes(currentUser.user_role)) {
        router.replace("/login");
      } else {
        setChecking(false);
      }
    } else if (!storedToken) {
      router.replace("/login");
    }
  }, [user, allowedRoles, router, dispatch]);

  if (checking) return <p>Đang kiểm tra quyền vc...</p>;

  return <>{children}</>;
}
