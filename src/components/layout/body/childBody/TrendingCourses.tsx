import React from "react";
import CardDes from "@/components/ui/card-des";

const TrendingCourses = () => {
  return (
    <section id="trend" className="w-full bg-white py-16">
      <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-16">
        {/* Title */}
        <div className="mb-10 text-center md:text-left">
          <h2 className="text-2xl md:text-3xl font-bold text-black">
            Nội dung nổi bật
          </h2>
          <p className="text-gray-500 mt-2 text-sm md:text-base">
            Các bài kiểm tra và nội dung thể lực phổ biến nhất hiện nay
          </p>
        </div>

        {/* Grid Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          <CardDes
            img="Video"
            title="Chạy 1000m"
            description="Kiểm tra sức bền và tốc độ"
            star={4}
            money={0}
            trending="Hot"
          />
          <CardDes
            img="Video"
            title="BMI Test"
            description="Đánh giá chỉ số cơ thể"
            star={5}
            money={0}
            trending="Hot"
          />
          <CardDes
            img="Video"
            title="Hít đất"
            description="Kiểm tra sức mạnh thân trên"
            star={4}
            money={0}
            trending=""
          />
          <CardDes
            img="Video"
            title="Gập bụng"
            description="Đánh giá cơ bụng"
            star={4}
            money={0}
            trending=""
          />
        </div>
      </div>
    </section>
  );
};

export default TrendingCourses;
