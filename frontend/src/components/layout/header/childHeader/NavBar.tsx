"use client";

import { Button } from "@/components/ui/button";
import { Menubar, MenubarMenu, MenubarTrigger } from "@/components/ui/menubar";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavBarItemProps {
  href: string;
  children: React.ReactNode;
  isActive?: boolean;
}

const NavBarItem = ({ href, children, isActive }: NavBarItemProps) => {
  return (
    <MenubarMenu>
      <MenubarTrigger>
        <Link href={href} className={cn(isActive && "text-2xl text-red-300")}>
          {children}
        </Link>
      </MenubarTrigger>
    </MenubarMenu>
  );
};

const navBarItem = [
  { href: "#home", children: "Trang chủ" },
  { href: "#trend", children: "Khám phá" },
  { href: "#introduce", children: "Giới thiệu" },
  { href: "#contact", children: "Liên hệ" },
];

export default function NavMenu() {
  const pathname = usePathname();
  return (
    <Menubar className="flex rounded-none border-0">
      <div className="flex-1"></div>

      {navBarItem.map(({ href, children }, index) => {
        return (
          <NavBarItem
            key={index}
            href={href}
            children={children}
            isActive={pathname === href}
          />
        );
      })}
    </Menubar>
  );
}
