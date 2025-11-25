"use client";

import { useState, ChangeEvent, FormEvent, useEffect } from "react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogDescription,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface UserDialogProps {
  onSuccess: () => void;
  triggerText?: string;
  defaultData?: Partial<FormData>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FormData {
  user_id: string;
  user_name: string;
  full_name: string;
  email: string;
  phone_number: string;
  user_code: string;
  password?: string;
  user_role: string;
  date_of_birth: string;
}

export function UserDialog({
  onSuccess,
  triggerText,
  defaultData = {},
  open,
  onOpenChange,
}: UserDialogProps) {
  const { post, put } = useApi();
  const isEdit = Boolean(defaultData.user_code);

  const [formData, setFormData] = useState<FormData>({
    user_id: "",
    user_name: "",
    full_name: "",
    email: "",
    phone_number: "",
    user_code: "",
    password: "",
    user_role: "",
    date_of_birth: "",
  });

  useEffect(() => {
    if (defaultData) {
      setFormData({
        user_id: defaultData.user_id || "",
        user_name: defaultData.user_name || "",
        full_name: defaultData.full_name || "",
        email: defaultData.email || "",
        phone_number: defaultData.phone_number || "",
        user_code: defaultData.user_code || "",
        password: "",
        user_role: defaultData.user_role || "",
        date_of_birth: defaultData.date_of_birth || "",
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

  // Call api khi submit
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      if (isEdit) {
        const data = await put(`/user/${formData.user_id}`, formData);
        toast.success(data.message || "Cập nhật thành công");
      } else {
        const data = await post("/user/register", formData);
        toast.success(data.message || "Thêm mới thành công");
      }
      onSuccess();
      onOpenChange(false); // đóng Dialog sau khi submit
    } catch (err: any) {
      toast.error(err?.message || "Đã xảy ra lỗi");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>
              {isEdit ? "Cập nhật người dùng" : "Thêm mới người dùng"}
            </DialogTitle>
            <DialogDescription>
              {isEdit
                ? "Điền các thông tin để cập nhật người dùng."
                : "Điền các thông tin để thêm người dùng mới."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-1">
              <Label>Tên đăng nhập</Label>
              <Input
                name="user_name"
                value={formData.user_name}
                onChange={handleChange}
                placeholder="Tên đăng nhập..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Họ và tên</Label>
              <Input
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                placeholder="Họ tên..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Email</Label>
              <Input
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Email..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Số điện thoại</Label>
              <Input
                name="phone_number"
                value={formData.phone_number}
                onChange={handleChange}
                placeholder="Số điện thoại..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Mã sinh viên</Label>
              <Input
                name="user_code"
                value={formData.user_code}
                onChange={handleChange}
                placeholder="MSSV..."
                disabled={isEdit}
              />
            </div>

            <div className="grid gap-1">
              <Label>Mật khẩu {isEdit ? "(để trống nếu không đổi)" : ""}</Label>
              <Input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Mật khẩu..."
              />
            </div>

            <div className="grid gap-1">
              <Label>Vai trò</Label>
              <Select
                onValueChange={(value) =>
                  handleChange({ target: { name: "user_role", value } })
                }
                value={formData.user_role}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Chọn vai trò" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="student">Student</SelectItem>
                  <SelectItem value="teacher">Teacher</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1">
              <Label>Ngày sinh</Label>
              <Input
                type="date"
                name="date_of_birth"
                value={formData.date_of_birth}
                onChange={handleChange}
              />
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
