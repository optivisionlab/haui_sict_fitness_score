"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { DataTable } from "@/components/table/data-table";
import { UserInf } from "./columns";

export default function UsersPage() {
  const { get } = useApi();
  const [users, setUsers] = useState<UserInf[]>([]);

  const getUsers = async () => {
    const data = await get("/user");
    setUsers(data);
  };

  useEffect(() => {
    getUsers();
  }, []);

  return (
    <div className="p-10">
      <h1 className="text-2xl font-bold mb-5 text-center">
        Quản lý người dùng
      </h1>
      <DataTable data={users} onReload={getUsers} />
    </div>
  );
}
