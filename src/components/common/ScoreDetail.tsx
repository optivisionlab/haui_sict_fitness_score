"use client";

import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import Image from "next/image";
import running from "@/image/training (2).png";
import Link from "next/link";
import { ScoreResult } from "@/types/scoreApiType";
import { calcRunInfo } from "@/lib/calcRunTime";

interface ScoreDetailProps {
  title?: string;
  caption?: string;
  data: ScoreResult[];
  userId: number;
  classId: number;
}

export default function ScoreDetail({
  title = "My Score Table",
  caption = "Bảng điểm chi tiết",
  data,
  userId,
  classId,
}: ScoreDetailProps) {
  const userCur = JSON.parse(sessionStorage.getItem("user") || "");
  const userIdCur = userCur.user_id;

  const hideCheckButton = userIdCur === userId; // TRUE = ẩn nút kiểm tra

  return (
    <div className="px-4 lg:px-8">
      <h1 className="text-2xl text-center mb-4 font-semibold">{title}</h1>

      <Table className="overflow-x-auto block lg:table shadow rounded-lg">
        <TableCaption>{caption}</TableCaption>

        <TableHeader>
          <TableRow>
            <TableHead className="w-[60px] text-center">STT</TableHead>
            <TableHead className="w-[200px]">Tên bài</TableHead>
            <TableHead>Trạng thái</TableHead>
            <TableHead className="hidden md:table-cell text-right">
              Điểm
            </TableHead>
            <TableHead className="text-center">Hành động</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {data.length > 0 ? (
            data.map((item, index) => {
              const info = calcRunInfo(item.start_time, item.end_time);

              return (
                <TableRow key={item.result_id} className="hover:bg-gray-50">
                  <TableCell className="text-center">{index + 1}</TableCell>

                  <TableCell>{item.exam_title}</TableCell>

                  <TableCell>
                    {item.avg_speed ? "Đã chấm" : "Chưa chấm"}
                  </TableCell>

                  <TableCell className="hidden md:table-cell text-right">
                    {item.avg_speed ?? "-"}
                  </TableCell>

                  {/* CHỈ CÒN 1 SHEET CHO MỌI NỀN TẢNG */}
                  <TableCell className="text-center">
                    {/* NÚT KIỂM TRA – CHỈ HIỆN NẾU KHÔNG TRÙNG USER */}
                    {hideCheckButton && (
                      <div className="hidden lg:inline-flex mr-1">
                        <Button variant="outline" size="sm">
                          <Link
                            href={`/scores/${userIdCur}_${classId}/${item.exam_id}`}
                          >
                            Kiểm tra
                          </Link>
                        </Button>
                      </div>
                    )}

                    <Sheet>
                      <SheetTrigger asChild>
                        <Button variant="outline" size="sm">
                          Chi tiết
                        </Button>
                      </SheetTrigger>

                      <SheetContent className="max-w-md p-0">
                        <SheetHeader className="p-4 border-b">
                          <SheetTitle>Thông số chấm điểm</SheetTitle>
                          <SheetDescription>
                            Thông tin chi tiết bài kiểm tra
                          </SheetDescription>
                        </SheetHeader>

                        <div className="p-4 space-y-3">
                          <p>
                            <strong>Tên bài kiểm tra:</strong> {item.exam_title}
                          </p>

                          <p>
                            <strong>Trạng thái:</strong>{" "}
                            {item.avg_speed ? "Đã chấm" : "Chưa chấm"}
                          </p>

                          <p>
                            <strong>Ngày kiểm tra:</strong> {item.exam_date}
                          </p>

                          <p>
                            <strong>Thời gian chạy:</strong>{" "}
                            {info.duration ?? "-"}
                          </p>

                          <p>
                            <strong>Bắt đầu:</strong> {info.start}
                          </p>

                          <p>
                            <strong>Kết thúc:</strong> {info.end}
                          </p>

                          <p>
                            <strong>Điểm:</strong> {item.avg_speed ?? "-"}
                          </p>

                          <div className="text-center mt-4">
                            <Image
                              src={running}
                              alt="run"
                              width={150}
                              height={150}
                              className="mx-auto"
                            />
                          </div>
                        </div>

                        {hideCheckButton && (
                          <SheetFooter className="p-4 border-t">
                            <SheetClose asChild>
                              <Button variant="outline" className="w-full">
                                <Link
                                  href={`/scores/${userIdCur}_${classId}/${item.exam_id}`}
                                >
                                  Đi đến kiểm tra
                                </Link>
                              </Button>
                            </SheetClose>
                          </SheetFooter>
                        )}
                      </SheetContent>
                    </Sheet>
                  </TableCell>
                </TableRow>
              );
            })
          ) : (
            <TableRow>
              <TableCell colSpan={5} className="text-center py-6 text-gray-500">
                Không có dữ liệu
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
