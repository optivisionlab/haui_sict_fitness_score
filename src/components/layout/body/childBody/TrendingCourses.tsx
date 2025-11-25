import React from "react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import CardDes from "@/components/ui/card-des";
const TrendingCourses = () => {
  return (
    <div id="trend">
      <h1 className="mt-[50px] mb-[15px]">Nội dung</h1>

      {/* Danh sach thinh hanh */}
      <div className="flex gap-5">
        <CardDes
          img="Video"
          title="Hoc JS"
          description="AI code"
          star={0}
          money={299.0}
          trending=""
        />
        <CardDes
          img="Video"
          title="Hoc JS"
          description="AI code"
          star={0}
          money={299.0}
          trending=""
        />{" "}
        <CardDes
          img="Video"
          title="Hoc JS"
          description="AI code"
          star={0}
          money={299.0}
          trending=""
        />{" "}
        <CardDes
          img="Video"
          title="Hoc JS"
          description="AI code"
          star={0}
          money={299.0}
          trending=""
        />{" "}
        <CardDes
          img="Video"
          title="Hoc JS"
          description="AI code"
          star={0}
          money={299.0}
          trending=""
        />
      </div>
    </div>
  );
};

export default TrendingCourses;
