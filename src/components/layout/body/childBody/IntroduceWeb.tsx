"use client";

const IntroduceWeb = () => {
  return (
    <section id="introduce" className="w-full py-20 bg-zinc-900 text-white">
      <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-16">
        {/* Tiêu đề */}
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-4xl font-bold">
            Chương Trình Hướng Tới
            <span className="text-red-500"> Mục Tiêu Của Bạn</span>
          </h2>
          <p className="text-zinc-400 mt-4 max-w-2xl mx-auto text-sm md:text-base">
            Hệ thống chấm điểm thể lực giúp bạn theo dõi tiến trình, cải thiện
            sức khỏe và nâng cao thành tích thông qua các tiêu chí đánh giá minh
            bạch.
          </p>
        </div>

        {/* Nội dung 3 cột */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-zinc-800 p-6 rounded-2xl hover:scale-105 transition duration-300">
            <h3 className="text-lg font-semibold mb-3 text-red-500">
              🎯 Đánh Giá Chính Xác
            </h3>
            <p className="text-zinc-400 text-sm">
              Tính điểm dựa trên các tiêu chí thể lực chuẩn như BMI, sức bền,
              tốc độ và sức mạnh.
            </p>
          </div>

          <div className="bg-zinc-800 p-6 rounded-2xl hover:scale-105 transition duration-300">
            <h3 className="text-lg font-semibold mb-3 text-red-500">
              📊 Theo Dõi Tiến Trình
            </h3>
            <p className="text-zinc-400 text-sm">
              Lưu trữ kết quả và xem sự cải thiện của bạn theo thời gian với
              biểu đồ trực quan.
            </p>
          </div>

          <div className="bg-zinc-800 p-6 rounded-2xl hover:scale-105 transition duration-300">
            <h3 className="text-lg font-semibold mb-3 text-red-500">
              🏆 Bảng Xếp Hạng
            </h3>
            <p className="text-zinc-400 text-sm">
              So sánh thành tích với bạn bè và cộng đồng để tăng động lực luyện
              tập.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default IntroduceWeb;
