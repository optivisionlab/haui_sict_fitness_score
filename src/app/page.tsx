"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

const page = () => {
  return (
    <div className="max-w-[400px] border-1 mx-auto mt-[100px] text-center h-[300px] p-[20px]">
      Sinh viên đăng nhập bằng mã sinh viên
      <Button className="mt-[200px]">
        <Link href={"/login"}>Đăng nhập bằng mã sinh viên</Link>
      </Button>
    </div>
  );
};

export default page;
