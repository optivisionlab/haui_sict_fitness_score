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

import { useState } from "react";
import { ClassDialog } from "@/components/common/ClassDialog";

export interface ClassInf {
  class_id: string;
  class_name: string;
  course_type: string;
  start_date: string;
  end_date: string;
  description: string;
  teacher_id: number;
  class_status: string;
}

export const getClassColumns = (
  onReload: () => void
): ColumnDef<ClassInf>[] => [
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
    accessorKey: "class_name",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Mã lớp học <ArrowUpDown />
      </Button>
    ),
  },
  { accessorKey: "course_type", header: "Loại" },
  {
    accessorKey: "start_date",
    header: "Ngày bắt đầu",
    cell: ({ row }) => <div>{row.getValue("start_date")}</div>,
  },
  { accessorKey: "end_date", header: "Ngày kết thúc" },
  { accessorKey: "teacher_id", header: "Giáo viên phụ trách" },
  { accessorKey: "description", header: "Mô tả" },
  { accessorKey: "class_status", header: "Trạng thái" },

  {
    id: "actions",
    cell: ({ row }) => {
      const { remove } = useApi();
      const classD = row.original;

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
                onClick={() => navigator.clipboard.writeText(classD.class_id)}
              >
                Copy mã lớp
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
                  await remove(`/class/${classD.class_id}`);
                  toast.success("Xoá thành công");
                  onReload();
                }}
              >
                Xóa
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Dialog controlled */}
          <ClassDialog
            open={openDialog}
            onOpenChange={setOpenDialog}
            onSuccess={onReload}
            defaultData={classD}
          />
        </>
      );
    },
  },
];
