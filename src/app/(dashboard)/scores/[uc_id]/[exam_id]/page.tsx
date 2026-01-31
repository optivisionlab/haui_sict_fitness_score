"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { toast } from "sonner";
import HistoryList from "@/components/history/ListHistory";
import ExamInfoCard from "@/components/run_action/ExamInfoCard";

export default function TestDetailPage() {
  const { get, post } = useApi();
  const params = useParams();
  const { exam_id } = params;

  const [step, setStep] = useState<number>(0);
  const [examInfo, setExamInfo] = useState<any>(null);
  const [history, setHistory] = useState([]);
  const [isRunning, setIsRunning] = useState(false);

  // Lấy user_id & class_id trong URL, tách bằng map
  const raw = String(params.uc_id);
  if (!raw.includes("_")) return <div>URL không hợp lệ</div>;
  const [user_id, class_id] = raw.split("_").map(Number);

  // Gọi API sau khi bài kiểm tra kết thúc
  const fetchData = async () => {
    try {
      const res = await get(
        `/class/${class_id}/user/${user_id}/exam/${exam_id}/results`,
      );
      const rows = res.rows ?? [];

      // console.log(rows[rows.length - 1].step + 1);
      if (rows.length < 1) {
        setStep(1);
      } else {
        setStep(rows[0].step + 1);
      }

      setExamInfo(rows[rows.length - 1] ?? null);
      setHistory(rows);
    } catch (err) {
      toast.error("Không thể tải dữ liệu bài kiểm tra");
    }
  };

  // load dữ liệu lần đầu
  useEffect(() => {
    fetchData();
  }, [exam_id]);

  function toMicroISOString(date: Date) {
    const iso = date.toISOString();
    // iso = "2025-11-10T22:40:52.563Z"

    const withoutZ = iso.replace("Z", ""); // "2025-11-10T22:40:52.563"
    const micro = withoutZ + "000"; // "2025-11-10T22:40:52.563000"

    return micro;
  }

  // Hàm bắt đầu kiểm tra
  const handleStart = async (startTime: number) => {
    const timestamp = toMicroISOString(new Date(startTime));
    console.log("Start time gửi lên server:", timestamp);

    setIsRunning(true);
    setExamInfo(null);

    console.log(`/exam/${exam_id}/user/${user_id}/${step}/start`);
    try {
      await post(`/exam/${exam_id}/user/${user_id}/${step}/start`, {
        user_id: user_id.toString(),
        exam_id: exam_id?.toString(),
        step: step,
        start_time: timestamp.toString(), // gửi microsecond chính xác
      });

      toast.success("Đã bắt đầu kiểm tra");
    } catch (error) {
      toast.error("Không thể gửi thời gian bắt đầu");
    }
  };

  // Cập nhật quá trình kiểm tra qua các cam
  // Lắng nghe realtime từ Redis qua WebSocket
  useEffect(() => {
    if (!user_id || !isRunning) return;

    const url = `${process.env.NEXT_PUBLIC_API_URL}/redis/events/user/${user_id}`;

    const es = new EventSource(url);

    es.onopen = () => console.log("SSE connected");

    es.addEventListener("checkin", (event) => {
      console.log("Receive CHECKIN event:", event.data);

      const payload = JSON.parse(event.data);

      // Trường hợp Redis chỉ gửi message
      if (payload.message) {
        toast.info(payload.message);
      }

      // Nếu server có gửi value kèm theo
      if (payload.value) {
        setExamInfo((prev: any) => ({
          ...prev,
          ...payload.value,
        }));

        [1, 2, 3, 4].forEach((i) => {
          const flag = payload.value[`flag_${i}`];
          if (flag !== undefined) {
            toast.info(`UPDATE flag_${i}: ${flag}`);
          }
        });
      }
    });

    es.onerror = () => {
      console.log("SSE error or closed");
      es.close();
    };

    return () => es.close();
  }, [user_id, isRunning]);

  // Hàm kết thúc kiểm tra
  const handleFinish = async (endTime: number, elapsed: number) => {
    console.log("Kết thúc lúc:", new Date(endTime).toLocaleString());
    console.log("Tổng thời gian chạy:", Math.floor(elapsed / 1000), "giây");

    const timestamp_end = toMicroISOString(new Date(endTime));

    try {
      await post(`/exam/${exam_id}/user/${user_id}/${step}/end`, {
        user_id: user_id.toString(),
        exam_id: exam_id?.toString(),
        step: step,
        end_time: timestamp_end.toString(), // gửi microsecond chính xác
      });

      toast.success("Chúc mừng bạn đã hoàn thành bài kiểm tra");
    } catch (error) {
      toast.error("Không thể gửi thời gian kết thúc");
    }

    setIsRunning(false);
    fetchData();
  };

  return (
    <div className="p-4 lg:p-8 space-y-6 mt-[50px]">
      <h1>Kết quả lần kiểm tra gần nhất</h1>
      <ExamInfoCard
        examInfo={examInfo}
        isRunning={isRunning}
        onStart={handleStart}
        onFinish={handleFinish}
      />

      <HistoryList history={history} />
    </div>
  );
}
