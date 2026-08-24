import { cn } from "@/lib/utils";
import React from "react";
import Notification from "./Notification";
import { time } from "console";
const page = () => {
  return (
    <div className={cn("p-[var(--paddingDiv)]")}>
      <h1 className={cn("text-2xl text-blue-500 mb-[var(--distanceAll)]")}>
        Thông báo
      </h1>
      <div>
        <Notification
          id={1}
          infor={"Giáo viên đã chấm bài tx1 của bạn"}
          time={2}
        />
        <Notification
          id={2}
          infor={"Giáo viên đã chấm bài tx2 của bạn"}
          time={1}
        />
      </div>
    </div>
  );
};

export default page;
