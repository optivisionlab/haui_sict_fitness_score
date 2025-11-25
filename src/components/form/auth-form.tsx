"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Schema validation
const formSchema = z.object({
  name: z
    .string()
    .min(2, { message: "Tên phải có ít nhất 2 kí tự" })
    .optional(),
  email: z.string().email({ message: "Email không hợp lệ." }),
  password: z
    .string()
    .min(8, { message: "Mật khẩu ít nhất 8 ký tự" })
    .regex(/[a-zA-Z]/, { message: "Phải chứa ít nhất 1 chữ cái" })
    .regex(/[0-9]/, { message: "Phải chứa ít nhất 1 số" })
    .regex(/[^a-zA-Z0-9]/, { message: "Phải chứa ít nhất 1 ký tự đặc biệt" }),
});

interface AuthFormProps {
  type: "login" | "register";
  onSubmit: (data: { email: string; password: string; name?: string }) => void;
}

export default function AuthForm({ type, onSubmit }: AuthFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{type === "login" ? "Đăng nhập" : "Đăng ký"}</CardTitle>
        <CardDescription>
          Nhập thông tin bên dưới để{" "}
          {type === "login" ? "đăng nhập" : "đăng ký"}
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 max-w-sm mx-auto"
        >
          {type === "register" && (
            <div>
              <Label htmlFor="name">Tên của bạn</Label>
              <Input id="name" {...register("name")} placeholder="Tên" />
              {errors.name && (
                <p className="text-red-500 text-sm">{errors.name.message}</p>
              )}
            </div>
          )}

          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              {...register("email")}
              placeholder="Email"
            />
            {errors.email && (
              <p className="text-red-500 text-sm">{errors.email.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="password">Mật khẩu</Label>
            <Input
              id="password"
              type="password"
              {...register("password")}
              placeholder="Mật khẩu"
            />
            {errors.password && (
              <p className="text-red-500 text-sm">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full">
            {type === "login" ? "Đăng nhập" : "Đăng ký"}
          </Button>
        </form>
      </CardContent>

      <CardFooter className="flex-col gap-2">
        <Button variant="outline" className="w-full">
          {type === "login" ? "Đăng nhập" : "Đăng ký"} với Google
        </Button>
        <Button asChild variant="link" className="p-0">
          {type === "login" ? (
            <Link href="/register">Chưa có tài khoản? Đăng ký</Link>
          ) : (
            <Link href="/login">Đã có tài khoản? Đăng nhập</Link>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
