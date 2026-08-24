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

interface card {
  img: string;
  title: string;
  description: string;
  star: number;
  money: number;
  trending: string;
}
const CardDes = ({ img, title, description, star, money, trending }: card) => {
  return (
    <Card className="w-[200px] p-0 border-0">
      <CardHeader>
        <p>{img}</p>
      </CardHeader>

      <CardContent>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
        <div>{star}</div>
        <div>{money}</div>
      </CardContent>

      <CardFooter>
        <p>{trending}</p>
      </CardFooter>
    </Card>
  );
};

export default CardDes;
