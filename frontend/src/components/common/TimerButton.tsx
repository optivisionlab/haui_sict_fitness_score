"use client";

import React, { useState, useEffect, useRef } from "react";
import CustomButton from "./CustomButton";

interface TimerButtonProps {
  running: boolean;
  onStart: (time: number) => void;
  onStop: (time: number, elapsed: number) => void;
}

export default function TimerButton({ running, onStart, onStop }: TimerButtonProps) {
  const [elapsed, setElapsed] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Khi trạng thái chạy thay đổi (đến từ cha)
  useEffect(() => {
    if (running) {
      const now = Date.now();
      setStartTime(now);

      intervalRef.current = setInterval(() => {
        setElapsed(Date.now() - now);
      }, 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setElapsed(0);
      setStartTime(null);
    }
  }, [running]);

  const handleStart = () => {
    const now = Date.now();
    onStart(now); //  gửi thời gian bắt đầu lên cha
  };

  const handleStop = () => {
    const end = Date.now();
    onStop(end, elapsed); //  gửi thời gian kết thúc & tổng ms lên cha
  };

  const formatTime = (ms: number) => {
    const sec = Math.floor(ms / 1000);
    return `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(
      sec % 60
    ).padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col items-center gap-2">
      {!running ? (
        <CustomButton label="Bắt đầu" onClick={handleStart} />
      ) : (
        <CustomButton label="Kết thúc" onClick={handleStop} />
      )}

      {running && (
        <p className="text-lg font-semibold text-green-600">
          ⏳ {formatTime(elapsed)}
        </p>
      )}
    </div>
  );
}
