"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { ArrowUpDown, MoreHorizontal } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

import { useApi } from "@/hooks/useApi";
import { toast } from "sonner";

import { UserDialog } from "@/components/common/UserDialog";
import { useState } from "react";
import { UserType } from "@/types/userType";

export interface UserInf {
  user_id: string;
  user_name: string;
  full_name: string;
  phone_number: string;
  user_code: string;
  user_role: string;
  date_of_birth: string;
}

export const getUserColumns = (onReload: () => void): ColumnDef<UserInf>[] => [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() ||
          (table.getIsSomePageRowsSelected() && "indeterminate")
        }
        onCheckedChange={(v) => table.toggleAllPageRowsSelected(!!v)}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(v) => row.toggleSelected(!!v)}
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "user_name",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Tên đăng nhập <ArrowUpDown />
      </Button>
    ),
  },
  { accessorKey: "full_name", header: "Họ và tên" },
  {
    accessorKey: "user_code",
    header: "Mã sinh viên",
    cell: ({ row }) => <div>{row.getValue("user_code")}</div>,
  },
  { accessorKey: "phone_number", header: "Số điện thoại" },
  { accessorKey: "user_role", header: "Vai trò" },
  { accessorKey: "date_of_birth", header: "Ngày sinh" },

  {
    id: "actions",
    cell: ({ row }) => {
      const { remove } = useApi();
      const user = row.original;

      const [openDialog, setOpenDialog] = useState(false);

      return (
        <>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="w-8 h-8 p-0">
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Chức năng</DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => navigator.clipboard.writeText(user.user_code)}
              >
                Copy mã sinh viên
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => {
                  setOpenDialog(true);
                }}
              >
                Sửa
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-red-500"
                onClick={async () => {
                  await remove(`/user/${user.user_id}`);
                  toast.success("Xoá thành công");
                  onReload();
                }}
              >
                Xóa
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Dialog controlled */}
          <UserDialog
            open={openDialog}
            onOpenChange={setOpenDialog}
            onSuccess={onReload}
            defaultData={user}
          />
        </>
      );
    },
  },
];
