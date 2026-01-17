import React, { useState } from "react";

// Mock data từ API
const mockData = {
  count: 5,
  images: [
    {
      camera_id: 1,
      checkin_time: "2025-12-11T10:30:00",
      image_url: "https://placehold.co/400x250?text=Camera+1",
    },
    {
      camera_id: 2,
      checkin_time: "2025-12-11T10:25:00",
      image_url: "https://placehold.co/400x250?text=Camera+2",
    },
    {
      camera_id: 3,
      checkin_time: "2025-12-11T10:20:00",
      image_url: "https://placehold.co/400x250?text=Camera+3",
    },
    {
      camera_id: 4,
      checkin_time: "2025-12-11T10:15:00",
      image_url: "https://placehold.co/400x250?text=Camera+4",
    },
  ],
};

export default function CameraMonitoringDemo() {
  const [selectedCam, setSelectedCam] = useState(null);

  return (
    <div className="flex h-screen bg-neutral-900 text-white">
      {/* LEFT: Camera grid giống YouTube */}
      <div className="flex-1 p-4">
        <div className="grid grid-cols-2 gap-4">
          {mockData.images.map((cam) => (
            <div
              key={cam.camera_id}
              onClick={() => setSelectedCam(cam)}
              className="relative cursor-pointer rounded-2xl overflow-hidden bg-black shadow-lg"
            >
              <img
                src={cam.image_url}
                alt={`Camera ${cam.camera_id}`}
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-2 left-2 bg-black/70 px-2 py-1 rounded text-sm">
                Cam {cam.camera_id}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT: Danh sách người đi qua */}
      <div className="w-[360px] border-l border-white/10 bg-neutral-950 p-4 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Người vừa xuất hiện</h2>

        {mockData.images.map((item, index) => (
          <div
            key={index}
            className="flex gap-3 mb-4 cursor-pointer hover:bg-white/5 p-2 rounded-xl"
          >
            <img
              src={item.image_url}
              alt="thumb"
              className="w-24 h-16 object-cover rounded-lg"
            />
            <div className="flex-1">
              <p className="font-medium">Camera {item.camera_id}</p>
              <p className="text-sm text-white/60">
                Thời gian: {new Date(item.checkin_time).toLocaleTimeString()}
              </p>
              <p className="text-xs text-white/40">ID người: #{index + 101}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
