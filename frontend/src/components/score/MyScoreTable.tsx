"use client";

import ScoreDetail from "@/components/common/ScoreDetail";
import { ScoreResult } from "@/types/scoreApiType";

interface MyScoreTableProps {
  data: ScoreResult[];
  userId: string | number;
  classId: string | number;
}

export default function MyScoreTable({ data, userId, classId }: MyScoreTableProps) {
  return (
    <ScoreDetail
      title="Bảng điểm của tôi"
      caption="Chi tiết điểm các bài kiểm tra"
      data={data}
      userId={typeof userId === "string" ? parseInt(userId) : userId}
      classId={typeof classId === "string" ? parseInt(classId) : classId}
    />
  );
}
