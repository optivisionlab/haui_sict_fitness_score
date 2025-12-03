"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

const Page = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white shadow-lg rounded-2xl p-10 w-full max-w-sm text-center border">
        <h2 className="text-2xl font-bold mb-3 text-gray-800">
          Sinh viên đăng nhập
        </h2>

        <p className="text-gray-600 mb-8">
          Vui lòng đăng nhập bằng mã sinh viên để tiếp tục truy cập hệ thống.
        </p>

        <Button className="w-full py-6 text-lg font-semibold">
          <Link href="/login" className="w-full block">
            Đăng nhập bằng mã sinh viên
          </Link>
        </Button>
      </div>
    </div>
  );
};

export default Page;
