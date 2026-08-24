"use client";

import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAppSelector } from "@/redux/hooks";
import { useApi } from "@/hooks/useApi";
import { toast } from "sonner";

interface UserProfile {
  full_name: string;
  user_code: string;
  phone_number: string;
  email: string;
  date_of_birth: string;
}

export default function EditInfor() {
  const { get, put } = useApi();
  const reduxUser = useAppSelector((state) => state.auth.user);

  const [isEdit, setIsEdit] = useState(false);
  const [loading, setLoading] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

  const [formData, setFormData] = useState<UserProfile>({
    full_name: "",
    user_code: "",
    phone_number: "",
    email: "",
    date_of_birth: "",
  });

  // Sync redux user khi load
  useEffect(() => {
    if (reduxUser) {
      setFormData({
        full_name: reduxUser.full_name || "",
        user_code: reduxUser.user_code || "",
        phone_number: reduxUser.phone_number || "",
        email: reduxUser.email || "",
        date_of_birth: reduxUser.date_of_birth
          ? typeof reduxUser.date_of_birth === "string"
            ? reduxUser.date_of_birth
            : (reduxUser.date_of_birth as any).toISOString?.().split("T")[0] || ""
          : "",
      });
    }
  }, [reduxUser]);

  // Fetch user từ API
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await get("/user/me");
        setFormData(data);
      } catch (error: any) {
        toast.error("Không thể tải thông tin người dùng");
      }
    };

    fetchUser();
  }, []);

  // Xử lý thay đổi
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const previewUrl = URL.createObjectURL(file);
      setAvatarPreview(previewUrl);

      // Cleanup tránh memory leak
      return () => URL.revokeObjectURL(previewUrl);
    },
    [],
  );

  // Lưu thông tin
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setLoading(true);
      await put("/user/me", formData);
      toast.success("Cập nhật thành công");
      setIsEdit(false);
    } catch (error: any) {
      toast.error("Cập nhật thất bại");
    } finally {
      setLoading(false);
    }
  };

  if (!reduxUser) {
    return <div className="text-center pt-20">Đang tải thông tin...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-4xl mx-auto">
        <Card className="shadow-xl rounded-2xl border-0">
          <CardContent className="p-6 md:p-10">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
              <h2 className="text-2xl font-bold">Thông tin cá nhân</h2>

              <Button
                variant={isEdit ? "secondary" : "default"}
                onClick={() => setIsEdit(!isEdit)}
                className="w-full md:w-auto"
              >
                {isEdit ? "Hủy chỉnh sửa" : "Chỉnh sửa"}
              </Button>
            </div>

            <form onSubmit={handleSave}>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                {/* Avatar */}
                <div className="flex flex-col items-center md:items-start">
                  <div className="relative w-40 h-40 rounded-full overflow-hidden bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-lg font-semibold shadow-md group">
                    {avatarPreview ? (
                      <img
                        src={avatarPreview}
                        alt="Avatar"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span>AVATAR</span>
                    )}

                    {isEdit && (
                      <>
                        <label
                          htmlFor="avatar-upload"
                          className="absolute bottom-0 w-full bg-black/60 text-center py-2 text-sm cursor-pointer opacity-0 group-hover:opacity-100 transition"
                        >
                          Tải ảnh lên
                        </label>
                        <input
                          id="avatar-upload"
                          type="file"
                          accept="image/*"
                          onChange={handleFileChange}
                          className="hidden"
                        />
                      </>
                    )}
                  </div>
                </div>

                {/* Thông tin */}
                <div className="md:col-span-2">
                  {!isEdit ? (
                    <div className="space-y-4 text-sm md:text-base">
                      <InfoRow label="Họ tên" value={formData.full_name} />
                      <InfoRow
                        label="Mã sinh viên"
                        value={formData.user_code}
                      />
                      <InfoRow label="Email" value={formData.email} />
                      <InfoRow
                        label="Số điện thoại"
                        value={formData.phone_number}
                      />
                      <InfoRow
                        label="Ngày sinh"
                        value={formData.date_of_birth}
                      />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <InputField
                        label="Họ tên"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleChange}
                      />

                      <InputField
                        label="Mã sinh viên"
                        name="user_code"
                        value={formData.user_code}
                        onChange={handleChange}
                      />

                      <InputField
                        label="Số điện thoại"
                        name="phone_number"
                        value={formData.phone_number}
                        onChange={handleChange}
                      />

                      <InputField
                        label="Email"
                        name="email"
                        value={formData.email}
                        disabled
                      />

                      <InputField
                        label="Ngày sinh"
                        name="date_of_birth"
                        type="date"
                        value={formData.date_of_birth}
                        onChange={handleChange}
                      />
                    </div>
                  )}
                </div>
              </div>

              {isEdit && (
                <div className="mt-10 flex justify-end">
                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full md:w-auto px-8"
                  >
                    {loading ? "Đang lưu..." : "Lưu thay đổi"}
                  </Button>
                </div>
              )}
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Thông tin từng dòng - format
function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col md:flex-row md:justify-between border-b pb-3">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value || "-"}</span>
    </div>
  );
}

// Reusable Input Component
interface InputFieldProps {
  label: string;
  name: string;
  value: string;
  type?: string;
  disabled?: boolean;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

function InputField({
  label,
  name,
  value,
  type = "text",
  disabled = false,
  onChange,
}: InputFieldProps) {
  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      <Input
        name={name}
        value={value}
        type={type}
        disabled={disabled}
        onChange={onChange}
      />
    </div>
  );
}
