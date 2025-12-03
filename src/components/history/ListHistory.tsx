"use client";

export default function HistoryList({ history }: any) {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-md">
      <h2 className="text-xl font-semibold mb-4">Lịch sử kiểm tra</h2>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {history.map((item: any) => (
          <div
            key={item.result_id}
            className="p-4 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition cursor-pointer"
          >
            <h3 className="font-medium">Lần kiểm tra thứ {item.step}</h3>
            <p className="text-gray-500 mt-2">
              Trạng thái: {item.avg_speed ? "Đã chấm" : "Chưa chấm"}
            </p>
            <p className="text-gray-500 mt-2">
              Số vòng đã chạy: {item.lap ?? "-"}
            </p>
            <p className="text-gray-500 text-sm mt-1">
              Điểm: {item.avg_speed ?? "-"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
