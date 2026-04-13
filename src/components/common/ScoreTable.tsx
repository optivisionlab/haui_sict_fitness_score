"use client";

import { cn } from "@/lib/utils";
import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ScoreTableType } from "@/types/scoreTableType";

import { useAppSelector } from "@/redux/hooks";
import { useRouter } from "next/navigation";

interface ScoreTableProps {
  data: ScoreTableType[];
  classId?: number;
}

export default function ScoreTable({ data, classId }: ScoreTableProps) {
  const { user } = useAppSelector((state) => state.auth);
  const router = useRouter();

  const handleClick = (user_id: number, class_id: number) => {
    router.push(`/scores/${user_id}_${class_id}`);
  };
  return (
    <div
      className={cn(
        "lg:p-[var(--paddingDiv)] w-[100%] mx-auto relative mt-[10px]"
      )}
    >
      {/* Bảng điểm */}
      <Table className="border-2 mb-[var(--distanceAll)]">
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">STT</TableHead>
            <TableHead>Mã sinh viên</TableHead>
            <TableHead>Họ tên</TableHead>
            <TableHead>Số điện thoại</TableHead>
            <TableHead className="text-right">TX1</TableHead>
            <TableHead className="text-right">TX2</TableHead>
            <TableHead className="text-right">Điểm cuối</TableHead>
            <TableHead
              className={`text-center ${
                (user?.user_role === "student" ||
                  user?.user_role === "teacher") &&
                "hidden"
              }`}
            >
              Chức năng
            </TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {data.map((infor: any, index) => (
            <TableRow
              key={infor.user.user_id}
              className={cn(index % 2 !== 0 && "bg-[#f6f0f0]")}
              onClick={() => classId && handleClick(infor.user.user_id, classId)}
            >
              <TableCell className="font-medium">{index + 1}</TableCell>
              <TableCell>{infor.user.user_code}</TableCell>
              <TableCell>{infor.user.full_name}</TableCell>
              <TableCell>{infor.user.phone_number}</TableCell>

              <TableCell className="text-right">
                {infor.results?.[0]?.avg_speed ?? "-"}
              </TableCell>
              <TableCell className="text-right">
                {infor.results?.[1]?.avg_speed ?? "-"}
              </TableCell>
              <TableCell className="text-right">
                {infor.results?.[2]?.avg_speed ?? "-"}
              </TableCell>
              <TableCell
                className={`text-center ${
                  (user?.user_role === "student" ||
                    user?.user_role === "teacher") &&
                  "hidden"
                }`}
              >
                <Button>Sửa đổi</Button>
                <Button className="ml-[10px]">Xem chi tiết</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
