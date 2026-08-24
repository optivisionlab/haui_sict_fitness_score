import { cn } from "@/lib/utils";
import React from "react";
import Notification from "./Notification";
import { Button } from "@/components/ui/button";
const page = () => {
  return (
    <div className={cn("p-[var(--paddingDiv)]")}>
      <h1 className={cn("text-2xl text-blue-500 mb-[var(--distanceAll)]")}>
        Thông báo
      </h1>

      <div className="lg:flex gap-50">
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

        <div>
          <h1 className="mt-20 text-xl lg:mt-0">
            Thêm thông báo đến sinh viên
          </h1>
          <textarea
            name=""
            id=""
            className="w-[80%] h-[200px] border lg:w-[500px]"
          >
            Nhập thông báo nếu có
          </textarea>
          <Button className="block px-[20px]">Gửi</Button>
        </div>
      </div>
    </div>
  );
};

export default page;
