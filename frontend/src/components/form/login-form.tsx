import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSeparator,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";

import { useState } from "react";

// Tạo type cho login, gửi lên submit
type LoginFormProps = Omit<React.ComponentProps<"form">, "onSubmit"> & {
  onSubmit?: (data: { username: string; password: string }) => void | Promise<void>;
};
export function LoginForm({ className, onSubmit, ...props }: LoginFormProps) {
  // Tạo form lưu
  const [formData, setFormData] = useState({ username: "", password: "" });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData({ ...formData, [id]: value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSubmit) {
      onSubmit(formData);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={cn("flex flex-col gap-6", className)}
      {...props}
    >
      <FieldGroup>
        <div className="flex flex-col items-center gap-1 text-center">
          <h1 className="text-2xl font-bold">Đăng nhập</h1>
          <p className="text-muted-foreground text-sm text-balance">
            Nhập mã sinh viên của bạn bên dưới
          </p>
        </div>
        <Field>
          <FieldLabel htmlFor="username">Mã sinh viên</FieldLabel>
          <Input
            id="username"
            type="text"
            placeholder="2023**"
            required
            value={formData.username}
            onChange={handleChange}
          />
        </Field>
        <Field>
          <div className="flex items-center">
            <FieldLabel htmlFor="password">Password</FieldLabel>
            <a
              href="#"
              className="ml-auto text-sm underline-offset-4 hover:underline"
            >
              Bạn quên mật khẩu?
            </a>
          </div>
          <Input
            id="password"
            type="password"
            required
            value={formData.password}
            onChange={handleChange}
          />
        </Field>
        <Field>
          <Button type="submit">Đăng nhập</Button>
        </Field>
        <FieldSeparator></FieldSeparator>
      </FieldGroup>
    </form>
  );
}
