"use client";

import NavMenu from "../header/childHeader/NavBar";
import CarouselPage from "./childBody/CarouselPage";
import IntroduceWeb from "./childBody/IntroduceWeb";
import { ProgressDemo } from "./childBody/Progress";
import TrendingCourses from "./childBody/TrendingCourses";

const Body = () => {
  return (
    <div className="min-h-screen w-full">
      {/* Navbar */}
      <NavMenu />

      {/* Hero Section */}
      <section className="w-full py-16 px-4 md:px-8 lg:px-16 bg-gradient-to-b">
        <div className="max-w-7xl mx-auto text-center space-y-6">
          <h1 className="text-3xl md:text-5xl font-bold">
            Hệ thống <span className="text-red-500">Chấm Điểm Thể Dục</span>
          </h1>
          <p className="text-zinc-400 max-w-2xl mx-auto text-sm md:text-base">
            Theo dõi, đánh giá và cải thiện thể lực của bạn thông qua hệ thống
            tính điểm tự động, minh bạch và chính xác.
          </p>

          <div className="flex justify-center gap-4 flex-wrap">
            <button className="bg-red-500 hover:bg-red-600 transition px-6 py-3 rounded-full font-medium">
              Tính điểm ngay
            </button>
            <button className="border border-red-500 text-red-500 hover:bg-red-500 hover:text-white transition px-6 py-3 rounded-full font-medium">
              Xem bảng xếp hạng
            </button>
          </div>
        </div>
      </section>

      {/* Carousel / Banner */}
      <section className="w-full py-12 px-4 md:px-8 lg:px-16">
        <div className="max-w-7xl mx-auto">
          <CarouselPage />
        </div>
      </section>

      {/* Trending / Bài test phổ biến */}
      <section className="w-full py-12 px-4 md:px-8 lg:px-16">
        <div className="max-w-7xl mx-auto">
          <TrendingCourses />
        </div>
      </section>

      {/* Giới thiệu hệ thống */}
      <section className="w-full py-16 px-4 md:px-8 lg:px-16">
        <div className="max-w-7xl mx-auto">
          <IntroduceWeb />
        </div>
      </section>
    </div>
  );
};

export default Body;
