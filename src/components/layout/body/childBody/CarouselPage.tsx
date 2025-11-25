import { Card, CardContent } from "@/components/ui/card";
import Autoplay from "embla-carousel-autoplay";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";

const CarouselPage = () => {
  return (
    <div id="home">
      <div
        className="w-full mx-auto my-[10px]"
        style={{ height: "var(--carousel-height)" }}
      >
        <Carousel
          plugins={[
            Autoplay({
              delay: 10000,
            }),
          ]}
          className="w-full h-full relative "
        >
          <CarouselContent className="h-full">
            {Array.from({ length: 5 }).map((_, index) => (
              <CarouselItem key={index} className="h-full basis-full">
                {/* Lay h = h cua div dau tien */}
                <Card
                  className="w-full flex"
                  style={{ height: "var(--carousel-height)" }}
                >
                  <CardContent className="h-full flex-1 flex items-center justify-center">
                    <span className="text-4xl font-semibold">{index + 1}</span>
                  </CardContent>
                </Card>
              </CarouselItem>
            ))}
          </CarouselContent>

          <CarouselPrevious className="absolute left-[10px]" />
          <CarouselNext className="absolute right-[10px]" />
        </Carousel>
      </div>

      {/* Web Description */}
      <div className="mx-auto max-w-[90%]">
        <h3
          className="text-center my-[30px]"
          style={{ fontSize: "var(--font-size-des)" }}
        >
          Được hơn 17.000 công ty và hàng triệu học viên trên khắp thế giới tin
          dùng
        </h3>
        <div className="text-center flex justify-around">
          <div>LOGO 1</div>
          <div>LOGO 2</div>
          <div>LOGO 3</div>
          <div>LOGO 4</div>
        </div>
      </div>
    </div>
  );
};

export default CarouselPage;
