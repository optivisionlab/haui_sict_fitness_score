"use client";

import { UserCard } from "@/components/demo/UserCard";
import { useEffect, useState } from "react";
import Image from "next/image";
import { CameraBox } from "@/components/demo/CameraBox";

/* TYPES */
export interface CheckinEvent {
  user_id: string;
  start_time: string;
  last_time: string;
  img_url: string;
  step: string;
  last_cam: string; // dùng như camera_id (1–4)
  lap: string;
}

/* PAGE */
export default function RealtimePage() {
  const [cams, setCams] = useState<Record<number, CheckinEvent | null>>({
    1: null,
    2: null,
    3: null,
    4: null,
  });

  const [users, setUsers] = useState<CheckinEvent[]>([]);

  /* SSE */
  useEffect(() => {
    let cancelled = false;

    const connect = async () => {
      // Kết nối tới endpoint SSE
      const url = `${process.env.NEXT_PUBLIC_API_URL}/demo/events/global`;
      console.log("CONNECT STREAM:", url);

      // Thêm chấp nhận text/event-stream
      const res = await fetch(url, {
        headers: {
          Accept: "text/event-stream",
        },
      });

      if (!res.body) {
        console.error("Ko trả về gì cả từ stream");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (!cancelled) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE chuẩn: mỗi event kết thúc bằng \n\n
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() || "";

        for (const chunk of chunks) {
          const dataLine = chunk.split("\n").find((l) => l.startsWith("data:"));

          if (!dataLine) continue;

          try {
            const payload: CheckinEvent = JSON.parse(
              dataLine.replace("data:", "").trim(),
            );

            console.log("STREAM EVENT:", payload);

            const camId = Number(payload.last_cam);

            if (camId >= 1 && camId <= 4) {
              setCams((prev) => ({
                ...prev,
                [camId]: payload,
              }));
            }

            // setUsers((prev) => {
            //   if (prev.find((u) => u.user_id === payload.user_id)) return prev;
            //   return [payload, ...prev];
            // });
            setUsers((prev) => [payload, ...prev].slice(0, 100));
          } catch (err) {
            console.error("Parse error:", err);
          }
        }
      }
    };

    connect();

    return () => {
      cancelled = true;
      console.log("Stream closed");
    };
  }, []);

  /* UI */
  return (
    <div className="min-h-screen bg-gray-100 p-6 mt-15">
      {/* HEADER */}
      <header className="bg-white shadow px-6 py-4 mb-6 flex items-center justify-between rounded-xl">
        <div className="flex items-center gap-2">
          <span className="text-red-500 animate-pulse text-sm">● LIVE</span>
          <h1 className="text-lg font-bold">Camera Monitoring Dashboard</h1>
        </div>

        <span className="text-xs text-gray-500">Realtime via SSE</span>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* CAMERA GRID */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((cam) => (
            <CameraBox key={cam} camId={cam} data={cams[cam]} />
          ))}
        </div>

        {/* USER LIST */}
        <div className="bg-white rounded-2xl shadow p-4 flex flex-col max-h-[70vh]">
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            👥 User Activity
            <span className="text-xs text-gray-400">({users.length})</span>
          </h2>

          <div className="space-y-3 overflow-y-auto pr-1">
            {users.length === 0 && (
              <p className="text-gray-500 text-sm">Chưa có user nào</p>
            )}

            {users.map((u, index) => (
              <UserCard key={index} user={u} />
            ))}

            {/* {(users.length ? users : fakeUsers).map((u, index) => (
              <UserCard key={index} user={u} />
            ))} */}
          </div>
        </div>
      </div>
    </div>
  );
}




