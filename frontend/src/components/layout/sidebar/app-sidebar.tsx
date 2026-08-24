"use client";

import * as React from "react";
import {
  Home,
  Calendar,
  Inbox,
  Search,
  Settings,
  UserRoundPen,
  School,
  Bell,
} from "lucide-react";
import Link from "next/link";

import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarRail,
} from "@/components/ui/sidebar";
import { useApi } from "@/hooks/useApi";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  // Lấy role từ sessionStorage
  const { get } = useApi();
  const [role, setRole] = React.useState<string | null>(null);
  const [userId, setUserId] = React.useState<number>();
  const [studentClasses, setStudentClasses] = React.useState<any[]>([]);
  const [scoreMenuOpen, setScoreMenuOpen] = React.useState(false);

  React.useEffect(() => {
    const data = sessionStorage.getItem("user");

    if (data) {
      try {
        const parsed = JSON.parse(data);
        setUserId(parsed.user_id);
        setRole(parsed.user_role); // <- lấy role từ session
      } catch (err) {
        console.error("fetch role ở session thất bại", err);
      }
    }
  }, []);

  React.useEffect(() => {
    const fetchClasses = async () => {
      if (role) {
        try {
          // Gọi API lấy danh sách lớp
          const res = await get(`/class`);
          setStudentClasses(res); // Cập nhật danh sách lớp
        } catch (error) {
          console.error("Lỗi khi lấy danh sách lớp:", error);
        }
      }
    };

    fetchClasses(); // Gọi hàm fetchClasses khi role thay đổi
  }, [role]); // Chạy lại khi role thay đổi

  const menuByRole = {
    admin: [
      { title: "Trang chủ", url: "/admin", icon: Home },
      { title: "Quản lý người dùng", url: "/admin/users", icon: Calendar },
      { title: "Quản lý lớp học", url: "/admin/classes", icon: Calendar },
      { title: "Quản lý chấm điểm", url: "/admin/scores", icon: Search },
      { title: "Demo dự án", url: "/admin/demo", icon: Settings },
      { title: "Quản lý thông báo", url: "/admin/notifications", icon: Bell },
    ],
    teacher: [
      { title: "Trang chủ", url: "/teacher", icon: Home },
      {
        title: "Thông tin cá nhân",
        url: "/edit-information",
        icon: UserRoundPen,
      },
      {
        title: "Quản lý lớp học",
        icon: Calendar,
        isParent: true,
      },
      {
        title: "Quản lý bài kiểm tra",
        url: "/exams",
        icon: Calendar,
      },
      { title: "Gửi thông báo", url: "/teacher/notifications", icon: Bell },
    ],
    student: [
      { title: "Trang chủ", url: "/student", icon: Home },
      {
        title: "Thông tin cá nhân",
        url: "/edit-information",
        icon: UserRoundPen,
      },
      {
        title: "Xem thông tin lớp học",
        url: "/student/class-information",
        icon: School,
      },
      {
        title: "Kiểm tra & Xem điểm",
        icon: Search,
        isParent: true,
      },
      { title: "Thông báo", url: "/student/notifications", icon: Bell },
    ],
  } as const;

  // Chưa load session -> tránh crash
  if (!role) return null;

  const navItems = menuByRole[role as keyof typeof menuByRole] || [];

  return (
    <Sidebar
      collapsible="icon"
      {...props}
      className="mt-[60px] h-[calc(100vh-60px)] border-r"
    >
      <SidebarHeader />
      <SidebarContent>
        <SidebarMenu>
          {navItems.map((item: any) => {
            const Icon = item.icon;
            // Nếu là student → chèn submenu lớp dưới mục Kiểm tra & Xem điểm
            if (role === "student" && item.isParent) {
              return (
                <div key="scores-section">
                  {/* Nút toggle */}
                  <SidebarMenuItem className="text-center ml-3">
                    <SidebarMenuButton
                      className="flex items-center gap-3 font-medium cursor-pointer"
                      onClick={() => setScoreMenuOpen((prev) => !prev)}
                    >
                      <Icon className="h-5 w-5 text-muted-foreground" />
                      <span>{item.title}</span>

                      {/* Icon mũi tên */}
                      <span className="ml-auto text-xs">
                        {scoreMenuOpen ? "▲" : "▼"}
                      </span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>

                  {/* Submenu lớp học */}
                  {scoreMenuOpen &&
                    studentClasses.map((cls) => (
                      <SidebarMenuItem key={cls.class_id} className="ml-10">
                        <SidebarMenuButton asChild>
                          <Link
                            href={`/scores/${userId}_${cls.class_id}`}
                            className="flex items-center gap-2 text-sm"
                          >
                            📘 Lớp {cls.class_name}
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))}
                </div>
              );
            }

            if (role === "teacher" && item.isParent) {
              return (
                <div key="scores-section">
                  {/* Nút toggle */}
                  <SidebarMenuItem className="text-center ml-3">
                    <SidebarMenuButton
                      className="flex items-center gap-3 font-medium cursor-pointer"
                      onClick={() => setScoreMenuOpen((prev) => !prev)}
                    >
                      <Icon className="h-5 w-5 text-muted-foreground" />
                      <span>{item.title}</span>

                      {/* Icon mũi tên */}
                      <span className="ml-auto text-xs">
                        {scoreMenuOpen ? "▲" : "▼"}
                      </span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>

                  {/* Submenu lớp học */}
                  {scoreMenuOpen &&
                    studentClasses.map((cls) => (
                      <SidebarMenuItem key={cls.class_id} className="ml-10">
                        <SidebarMenuButton asChild>
                          <Link
                            href={`/teacher/classes/${cls.class_id}`}
                            className="flex items-center gap-2 text-sm"
                          >
                            📘 Lớp {cls.class_name}
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))}
                </div>
              );
            }

            return (
              <SidebarMenuItem key={item.title} className="text-center ml-3">
                <SidebarMenuButton asChild>
                  <Link
                    href={item.url}
                    className="flex items-center gap-3 font-medium"
                  >
                    <Icon className="h-5 w-5 text-muted-foreground" />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarContent>

      <SidebarRail />
    </Sidebar>
  );
}
