"use client";

import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppSidebar } from "@/components/layout/sidebar/app-sidebar";
import Header from "@/components/layout/header/Header";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    // Chỉ chạy ở client
    const token = sessionStorage.getItem("access_token");
    setAccessToken(token);

    if (!token) {
      router.push("/login");
      return;
    }

    // Kiểm tra token hết hạn
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      const isExpired = payload.exp * 1000 < Date.now();

      if (isExpired) {
        router.push("/login");
      }
    } catch (err) {
      console.error("Token parse error:", err);
      router.push("/login");
    }
  }, [router]);

  // Chưa load token => tránh render layout gây nháy màn hình
  if (accessToken === null) return null;

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "15rem",
          padding: "15px",
        } as React.CSSProperties
      }
    >
      <AppSidebar />
      <SidebarInset>
        <header className="flex w-auto h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1 z-2 mt-[120px]" />
          </div>
        </header>

        <main className="w-full p-[0px] md:overflow-auto">
          <Header />
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
