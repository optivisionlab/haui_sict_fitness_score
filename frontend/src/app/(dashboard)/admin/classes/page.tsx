"use client";

import React, { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { DataClass } from "@/components/table/data-class";
import { da } from "zod/v4/locales";

export interface ClassInf {
  class_id: string;
  class_name: string;
  course_type: string;
  start_date: string;
  end_date: string;
  description: string;
  teacher_id: number;
  class_status: string;
}
const CLassseManagerPage = () => {
  const { get } = useApi();
  const [classes, setClasses] = useState<ClassInf[]>([]);

  const getClasses = async () => {
    const data = await get("/class");
    setClasses(data);
  };

  useEffect(() => {
    getClasses();
  }, []);

  return (
    <div className="p-10">
      <h1 className="text-2xl font-bold mb-5 text-center">Quản lý lớp học</h1>
      <DataClass data={classes} onReload={getClasses} />
    </div>
  );
};

export default CLassseManagerPage;
