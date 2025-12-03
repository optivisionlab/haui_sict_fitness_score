"use client";

import ScoreDetail from "@/components/common/ScoreDetail";

export default function MyScoreTable({ data, userId, classId }: any) {
  return (
    <ScoreDetail
      title="Bảng điểm"
      caption="Chi tiết điểm các bài kiểm tra"
      data={data}
      userId={userId}
      classId={classId}
    />
  );
}
