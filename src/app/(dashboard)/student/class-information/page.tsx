"use client";

import sach from "@/image/sach.jpg";
import Image from "next/image";
import ScoreTable from "@/components/common/ScoreTable";
import { ScoreTableType } from "@/types/scoreTableType";
import { ClassType } from "@/types/classType";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { useAppSelector } from "@/redux/hooks";
import { toast } from "sonner";

export default function ClassInfor() {
  const { get } = useApi();
  const user = useAppSelector((state) => state.auth.user);

  const [classes, setClasses] = useState<ClassType[]>([]);
  const [selectedClass, setSelectedClass] = useState<ClassType | null>(null);
  const [studentList, setStudentList] = useState<ScoreTableType[]>([]);

  // Lấy danh sách lớp
  useEffect(() => {
    const fetchClasses = async () => {
      try {
        const data = await get(`/class`);
        setClasses(data?.items ?? data ?? []);
      } catch (error: any) {
        toast.error("Lỗi: " + error.message);
      }
    };
    fetchClasses();
  }, []);

  // Khi chọn lớp -> gọi API lấy danh sách học viên của lớp đó
  const handleSelectClass = async (cls: ClassType) => {
    setSelectedClass(cls);

    try {
      const data = await get(`/class/${cls.class_id}/exams/results/by-user`);
      // console.log(data);
      setStudentList(data.items);
    } catch (error: any) {
      toast.error("Lỗi khi tải danh sách học viên: " + error.message);
      console.error(error);
    }
  };

  return (
    <>
      <Image src={sach} alt="banner" className="w-full h-[50px] object-cover" />

      <div className="bg-white p-4">
        {/* Danh sách lớp */}
        <div className="mb-[var(--distanceAll)]">
          {classes.map((item) => (
            <Button
              key={item.class_id}
              onClick={() => handleSelectClass(item)}
              className={cn(
                "mr-[15px]",
                selectedClass?.class_id === item.class_id &&
                  "bg-blue-600 text-white"
              )}
            >
              Lớp {item.class_name}
            </Button>
          ))}
        </div>

        {/* Tiêu đề lớp */}
        {selectedClass && (
          <h1 className="text-2xl text-blue-500">
            Giáo viên đảm nhiệm: {selectedClass.teacher_id}
          </h1>
        )}

        {/* Hiển thị bảng điểm */}
        {studentList.length > 0 && selectedClass ? (
          <ScoreTable data={studentList} classId={selectedClass.class_id} />
        ) : (
          <p className="text-gray-500">
            {selectedClass
              ? "Lớp này chưa có dữ liệu điểm."
              : "Vui lòng chọn lớp để xem bảng điểm."}
          </p>
        )}
      </div>
    </>
  );
}
