"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { useEffect, useState } from "react";
import { useAppSelector } from "@/redux/hooks";
import { useApi } from "@/hooks/useApi";
import { toast } from "sonner";

export default function EditInfor() {
  const { put, get } = useApi();
  const user: any = useAppSelector((state) => state.auth.user);

  const [isEdit, setIsEdit] = useState<boolean>(false);
  const [avatar, setAvatar] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    full_name: user?.full_name || "",
    user_code: user?.user_code || "",
    phone_number: user?.phone_number || "",
    email: user?.email || "",
    date_of_birth: user?.date_of_birth || "",
  });

  // Xử lý thay đổi input text
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Xử lý thay đổi ảnh đại diện
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setAvatar(imageUrl);
    }
  };

  // Xử lý lưu thông tin
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Thông tin đã lưu:", formData);
    await put(`/user/me`, formData);
    toast.success("Cập nhật thành công");
    setIsEdit(false);
  };

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await get("/user/me");
        setFormData(data);
      } catch (err: any) {
        toast.error(err);
      }
    };

    fetchUser();
  }, []);

  if (!user) return <div className="text-center">Đang tải thông tin...</div>;

  return (
    <div className="min-w-[70%] pt-[100px] mx-[20px] md:mx-[100px]">
      <Button className="mb-[10px]" onClick={() => setIsEdit(!isEdit)}>
        {isEdit ? "Hủy chỉnh sửa" : "Sửa thông tin cá nhân"}
      </Button>

      <Card className="w-full mx-auto">
        <CardContent>
          <form className="w-full p-[20px]" onSubmit={handleSave}>
            {!isEdit ? (
              // ==== VIEW MODE ====
              <div className="mx-auto lg:flex gap-6">
                <div className="relative w-[150px] h-[150px] mx-auto flex items-center justify-center rounded-full bg-amber-300 text-white font-bold my-auto overflow-hidden">
                  {avatar ? (
                    <img
                      src={avatar}
                      alt="Avatar"
                      className="object-cover w-full h-full"
                    />
                  ) : (
                    <span>AVATAR</span>
                  )}
                </div>

                <div className="flex-1 w-full mt-[20px] mx-auto lg:ml-[50px]">
                  <div className="font-bold text-red-500">
                    {formData.full_name}
                  </div>
                  <div>Mã SV: {formData.user_code}</div>
                  <div>Email: {formData.email}</div>
                  <div>SĐT: {formData.phone_number}</div>
                  <div>Ngày sinh: {formData.date_of_birth}</div>
                </div>
              </div>
            ) : (
              // ==== EDIT MODE ====
              <div className="lg:flex gap-6">
                <div className="relative w-[150px] h-[150px] mx-auto flex items-center justify-center rounded-full bg-amber-300 text-white font-bold my-auto overflow-hidden group">
                  {avatar ? (
                    <img
                      src={avatar}
                      alt="Avatar"
                      className="object-cover w-full h-full"
                    />
                  ) : (
                    <span>AVATAR</span>
                  )}
                  <label
                    htmlFor="avatar-upload"
                    className="absolute bottom-0 w-full bg-black/50 text-center py-2 text-sm cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    Tải ảnh lên
                  </label>
                  <input
                    type="file"
                    id="avatar-upload"
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </div>

                <div className="flex-1 mt-[20px] lg:ml-[50px]">
                  <div className="grid gap-2 mb-[15px]">
                    <Label>Họ tên</Label>
                    <Input
                      name="full_name"
                      value={formData.full_name}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="grid gap-2 mb-[15px]">
                    <Label>Mã sinh viên</Label>
                    <Input
                      name="user_code"
                      value={formData.user_code}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="grid gap-2 mb-[15px]">
                    <Label>Số điện thoại</Label>
                    <Input
                      name="phone_number"
                      value={formData.phone_number}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="grid gap-2 mb-[15px]">
                    <Label>Email</Label>
                    <Input
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      disabled
                    />
                  </div>

                  <div className="grid gap-2 mb-[15px]">
                    <Label>Ngày sinh</Label>
                    <Input
                      type="date"
                      name="date_of_birth"
                      value={formData.date_of_birth}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </div>
            )}

            {isEdit && (
              <CardFooter className="mt-6 flex justify-end">
                <Button type="submit">Lưu thay đổi</Button>
              </CardFooter>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
