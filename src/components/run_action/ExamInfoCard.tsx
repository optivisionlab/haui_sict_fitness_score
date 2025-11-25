"use client";

import TimerButton from "@/components/common/TimerButton";

export default function ExamInfoCard({
  examInfo,
  isRunning,
  onStart,
  onFinish,
}: {
  examInfo: any;
  isRunning: boolean;
  onStart: (startTime: number) => void;
  onFinish: (endTime: number, elapsed: number) => void;
}) {
  // Khi đang chạy → hiển thị trạng thái rỗng
  const display = examInfo && !isRunning ? examInfo : {};

  return (
    <div className="bg-white p-6 rounded-2xl shadow-md flex flex-col lg:flex-row justify-between gap-6">
      {/* LEFT INFO */}
      <div className="flex-1 grid grid-cols-2 gap-4 lg:grid-cols-3">
        <DetailItem label="Bài kiểm tra" value={examInfo?.exam_title ?? ""} />
        <DetailItem label="Lần kiểm tra" value={examInfo?.step ?? ""} />
        <DetailItem
          label="Trạng thái"
          value={
            isRunning ? "Đang chạy..." : examInfo?.avg_speed ? "Đã chấm" : ""
          }
        />
        <DetailItem
          label="Ngày chạy"
          value={examInfo?.start_time?.slice(0, 10) ?? ""}
        />
        <DetailItem label="Điểm" value={examInfo?.avg_speed ?? ""} />
        <DetailItem label="Vòng" value={examInfo?.lap ?? ""} />
      </div>

      {/* RIGHT ACTION */}
      <TimerButton running={isRunning} onStart={onStart} onStop={onFinish} />
    </div>
  );
}

const DetailItem = ({ label, value }: { label: string; value: any }) => (
  <div>
    <h4 className="text-gray-500 text-sm">{label}</h4>
    <p className="font-medium text-lg min-h-[28px]">{value}</p>
  </div>
);
