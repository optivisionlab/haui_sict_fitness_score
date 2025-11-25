"use client";

import { useEffect, useState } from "react";
import ChartScore from "@/components/score/ChartScore";
import MyScoreTable from "@/components/score/MyScoreTable";
import { useParams } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import { toast } from "sonner";

export default function WatchScores() {
  const params = useParams();
  const { get } = useApi();

  const raw = String(params.uc_id);
  if (!raw.includes("_")) return <div>URL không hợp lệ</div>;

  const [user_id, class_id] = raw.split("_").map(Number);

  const [scoreData, setScoreData] = useState([]);
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const res = await get(
          `/class/${class_id}/user/${user_id}/exams/results/top`
        );

        const results = res.results ?? [];

        setScoreData(results);

        // Tạo chart data từ results (ví dụ uv = avg_speed)
        setChartData(
          results.map((item) => ({
            name: item.exam_title,
            uv: item.avg_speed ?? 0,
          }))
        );
      } catch (err) {
        toast.error("Không thể tải dữ liệu");
      }
    };

    loadData();
  }, []);
  return (
    <div className="p-4 flex flex-col lg:flex-row gap-5 mt-[50px]">
      <div className="w-full lg:w-3/5 border border-gray-300 rounded-2xl p-4 bg-white order-2 lg:order-1">
        <MyScoreTable data={scoreData} userId={user_id} classId={class_id} />
      </div>

      <div className="w-full lg:w-2/5 border border-gray-300 rounded-2xl p-4 bg-white order-1 lg:order-2">
        <ChartScore data={chartData} />
      </div>
    </div>
  );
}
