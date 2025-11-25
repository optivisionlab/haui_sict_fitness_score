"use client";

import { ModeToggle } from "@/components/mode-toggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAppDispatch } from "@/redux/hooks";
import { logoutThunk } from "@/features/auth/authThunks";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

const MainHeader = () => {
  const [user, setUser] = useState<any>(null);
  const dispatch = useAppDispatch();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const savedUser = sessionStorage.getItem("user");
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (err) {
        console.error("Lỗi parse user:", err);
      }
    }
  }, []);

  const handleLogout = async () => {
    await dispatch(logoutThunk());
    localStorage.removeItem("user");
    router.push("/login");
  };

  if (pathname === "/login") return null;

  return (
    <header
      className="flex z-10 bg-white justify-between items-center px-6 border-b border-gray-200 fixed top-0 right-0 left-0 shadow-sm"
      style={{ height: "var(--navHeight)" }}
    >
      {/* Logo */}
      <Link href="/" className="font-bold text-xl text-gray-800">
        LOGO
      </Link>

      <div className="flex items-center gap-4">
        <ModeToggle />

        {/* Avatar menu */}
        {user && (
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger>
              <Avatar className="cursor-pointer">
                <AvatarImage src={user.avatar_url || ""} />
                <AvatarFallback>
                  {user.username?.[0]?.toUpperCase() || "?"}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>

            <DropdownMenuContent
              className="mt-[var(--distanceDropdown)] p-[var(--distanceAll)]"
              align="end"
            >
              <DropdownMenuLabel className="flex gap-x-3 items-center">
                <Avatar>
                  <AvatarImage src={user.avatar_url || ""} />
                  <AvatarFallback>
                    {user.username?.[0]?.toUpperCase() || "?"}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-medium">{user.username}</p>
                  <p className="text-sm text-gray-500">{user.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />

              <DropdownMenuItem asChild>
                <Link href="/edit-information">Sửa thông tin cá nhân</Link>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={handleLogout}>
                Đăng xuất
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  );
};

export default MainHeader;
