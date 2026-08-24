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
import Image from "next/image";

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
      <Link href="/home" className="flex items-center gap-2 group select-none">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gray-100 group-hover:bg-gray-200 transition">
          <Image
            src="/logoHautoMLNotext.png"
            alt="AutoML Logo"
            width={28}
            height={28}
            className="object-contain"
          />
        </div>

        <span className="text-lg font-bold tracking-wide text-gray-800 group-hover:text-black transition">
          SICT
        </span>
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
                  {user.username?.[0]?.toUpperCase() || "C"}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>

            <DropdownMenuContent
              className="mt-[var(--distanceDropdown)] p-[var(--distanceAll)]"
              align="end"
            >
              <DropdownMenuLabel className="flex gap-x-3 items-center">
                <Avatar>
                  <AvatarImage
                    src={user.avatar_url || "/front-end/public/anhtest/2.jpg"}
                  />
                  <AvatarFallback>
                    {user.username?.[0]?.toUpperCase() || "C"}
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
