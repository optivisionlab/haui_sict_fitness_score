"use client";

import { Provider } from "react-redux";
import { store } from "./store";
import { setCredentials } from "@/features/auth/authSlice";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

export function ReduxProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const access_token = sessionStorage.getItem("access_token");
    const userStr = sessionStorage.getItem("user");

    if (access_token && userStr) {
      const user = JSON.parse(userStr);
      store.dispatch(setCredentials({ access_token, user }));

      if (pathname === "/" || pathname === "/login") {
        router.replace(`/${user.user_role}`);
      }
    }
  }, [pathname, router]);

  return <Provider store={store}>{children}</Provider>;
}
