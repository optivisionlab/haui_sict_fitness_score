"use client";
import NavMenu from "../header/childHeader/NavBar";
import CarouselPage from "./childBody/CarouselPage";
import IntroduceWeb from "./childBody/IntroduceWeb";
import { ProgressDemo } from "./childBody/Progress";
import TrendingCourses from "./childBody/TrendingCourses";

const Body = () => {
  return (
    <div className="h-auto w-[80%] mx-auto">
      {/* <ProgressDemo /> */}
      <NavMenu />
      <CarouselPage />
      <TrendingCourses />
      <IntroduceWeb />
    </div>
  );
};

export default Body;
