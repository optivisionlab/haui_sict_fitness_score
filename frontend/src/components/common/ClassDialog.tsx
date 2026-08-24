"use client";

import { useState, ChangeEvent, FormEvent, useEffect } from "react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ClassDialogProps {
  onSuccess: () => void;
  triggerText?: string;
  defaultData?: Partial<FormData>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FormData {
  class_id: string;
  class_name: string;
  course_type: string;
  start_date: string;
  end_date: string;
  description: string;
  teacher_id: number;
  class_status: string;
}

export function ClassDialog({
  onSuccess,
  triggerText,
  defaultData = {},
  open,
  onOpenChange,
}: ClassDialogProps) {
  const { post, put } = useApi();
  const isEdit = Boolean(defaultData.class_id);

  const [formData, setFormData] = useState<FormData>({
    class_id: "",
    class_name: "",
    course_type: "",
    start_date: "",
    end_date: "",
    description: "",
    teacher_id: 0,
    class_status: "",
  });

  useEffect(() => {
    if (defaultData) {
      setFormData({
        class_id: defaultData.class_id || "",
        class_name: defaultData.class_name || "",
        course_type: defaultData.course_type || "",
        start_date: defaultData.start_date || "",
        end_date: defaultData.end_date || "",
        description: defaultData.description || "",
        teacher_id: defaultData.teacher_id || 0,
        class_status: defaultData.class_status || "",
      });
    }
  }, [defaultData]);

  const handleChange = (
    e:
      | ChangeEvent<HTMLInputElement>
      | { target: { name: string; value: string } }
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (isEdit) {
        const data = await put(`/class/${formData.class_id}`, formData);
        toast.success(data.message || "Cập nhật lớp học thành công");
      } else {
        const data = await post("/class", formData);
        toast.success(data.message || "Thêm lớp học thành công");
      }
      onSuccess();
      onOpenChange(false);
    } catch (err: any) {
      toast.error(err?.message || "Đã xảy ra lỗi");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>
              {isEdit ? "Cập nhật lớp học" : "Thêm lớp học mới"}
            </DialogTitle>
            <DialogDescription>
              {isEdit
                ? "Điền các thông tin để cập nhật lớp học."
                : "Điền các thông tin để thêm lớp học mới."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-1">
              <Label>Tên lớp</Label>
              <Input
                name="class_name"
                value={formData.class_name}
                onChange={handleChange}
                placeholder="Tên lớp..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Loại khóa học</Label>
              <Input
                name="course_type"
                value={formData.course_type}
                onChange={handleChange}
                placeholder="Loại khóa học..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Ngày bắt đầu</Label>
              <Input
                type="date"
                name="start_date"
                value={formData.start_date}
                onChange={handleChange}
              />
            </div>

            <div className="grid gap-1">
              <Label>Ngày kết thúc</Label>
              <Input
                type="date"
                name="end_date"
                value={formData.end_date}
                onChange={handleChange}
              />
            </div>

            <div className="grid gap-1">
              <Label>Mô tả</Label>
              <Input
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Mô tả lớp học..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Giáo viên</Label>
              <Input
                type="number"
                name="teacher_id"
                value={formData.teacher_id}
                onChange={handleChange}
                placeholder="ID giáo viên..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Trạng thái lớp</Label>
              <Select
                value={formData.class_status}
                onValueChange={(value) =>
                  handleChange({ target: { name: "class_status", value } })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Chọn trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Đang hoạt động</SelectItem>
                  <SelectItem value="inactive">Ngừng hoạt động</SelectItem>
                  <SelectItem value="completed">Hoàn thành</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Huỷ</Button>
            </DialogClose>
            <Button type="submit">Lưu</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
