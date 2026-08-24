import { CalendarIcon } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import type { LucideIcon } from "lucide-react";

interface notifications {
  icon: LucideIcon;
  content: string;
  whoSend: string;
  time: String;
  link?: string;
}

export function HoverNotification({
  icon: Icon,
  content,
  whoSend,
  time,
  link,
}: notifications) {
  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <Icon />
      </HoverCardTrigger>

      <HoverCardContent
        className="w-80 mt-[var(--mtDropdown)] px-[20px]"
        align="end"
      >
        <div className="flex justify-between gap-4 mb-[20px]">
          <Avatar>
            <AvatarImage src="https://github.com/vercel.png" />
            {/* <AvatarFallback>Người gửi</AvatarFallback> */}
          </Avatar>

          <div className="space-y-1">
            <h4 className="text-sm font-semibold">{whoSend}</h4>
            <p className="text-sm">{content}</p>
            <div className="text-muted-foreground text-xs">{time}</div>
          </div>
        </div>

        <div className="flex justify-between gap-4">
          <Avatar>
            <AvatarImage src="https://github.com/vercel.png" />
            {/* <AvatarFallback>Người gửi</AvatarFallback> */}
          </Avatar>

          <div className="space-y-1">
            <h4 className="text-sm font-semibold">{whoSend}</h4>
            <p className="text-sm">{content}</p>
            <div className="text-muted-foreground text-xs">{time}</div>
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
