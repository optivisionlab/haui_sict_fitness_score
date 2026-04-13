"use client";

import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "../ui/input";
import { Button } from "../ui/button";

import { useState } from "react";
import { getUserColumns } from "@/app/(dashboard)/admin/users/columns";
import { UserDialog } from "../common/UserDialog";

interface DataTableProps {
  data: any[];
  onReload: () => void;
}

export function DataTable({ data, onReload }: DataTableProps) {
  const columns = getUserColumns(onReload);
  const [openDialog, setOpenDialog] = useState(false);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(), // Thiết lập lọc
    getSortedRowModel: getSortedRowModel(), // Thiết lập sắp xếp
    getPaginationRowModel: getPaginationRowModel(), // Tạo phân trang
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        {" "}
        {/* Input tìm theo mã sinh viên */}
        <Input
          placeholder="Lọc theo mã sinh viên..."
          value={
            (table.getColumn("user_code")?.getFilterValue() as string) ?? ""
          }
          onChange={(e) =>
            table.getColumn("user_code")?.setFilterValue(e.target.value)
          }
          className="max-w-sm"
        />
        <Button onClick={() => setOpenDialog(true)}>Thêm người dùng mới</Button>
      </div>

      {/* Bảng dữ liệu */}
      <div className="rounded-md border overflow-hidden">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>

          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center h-24"
                >
                  Không có dữ liệu
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-end gap-2">
        <div className="text-muted-foreground flex-1 text-sm">
          {table.getFilteredSelectedRowModel().rows.length} trong{" "}
          {table.getFilteredRowModel().rows.length} hàng được chọn.{" "}
        </div>

        <button
          className="px-3 py-1 border rounded"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          Trước
        </button>
        <button
          className="px-3 py-1 border rounded"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          Sau
        </button>
      </div>

      {/* Dialog controlled */}
      <UserDialog
        open={openDialog}
        onOpenChange={setOpenDialog}
        onSuccess={onReload}
        defaultData={[]}
      />
    </div>
  );
}
