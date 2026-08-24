"use client";

import { useEffect, useRef } from "react";
import Hls from "hls.js";

const CAM_BASE: Record<number, string | undefined> = {
  1: process.env.NEXT_PUBLIC_CAM_1_BASE,
  2: process.env.NEXT_PUBLIC_CAM_2_BASE,
  3: process.env.NEXT_PUBLIC_CAM_3_BASE,
  4: process.env.NEXT_PUBLIC_CAM_4_BASE,
};

export function CameraBox({
  camId,
  data,
}: {
  camId: number;
  data?: unknown;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!videoRef.current) return;

    const video = videoRef.current;

    // URL HLS đúng từ MediaMTX
    // const url = `http://10.1.12.88:8888/cam${camId}/video1_stream.m3u8`;
    const base = CAM_BASE[camId];

    if (!base) {
      console.error(`Missing base URL for cam ${camId}`);
      return;
    }
    
    const url = `${base}/cam${camId}/video1_stream.m3u8`;

    let hls: Hls | null = null;

    if (Hls.isSupported()) {
      hls = new Hls({
        lowLatencyMode: true,
        maxBufferLength: 3,
        liveSyncDuration: 1,
      });

      hls.loadSource(url);
      hls.attachMedia(video);

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error("HLS error:", data);
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari
      video.src = url;
    }

    return () => {
      if (hls) hls.destroy();
    };
  }, [camId]);

  return (
    <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
      
      {/* Title overlay */}
      <div className="absolute top-2 left-2 z-10 bg-black/60 text-white text-sm px-3 py-1 rounded-lg backdrop-blur">
        Camera {camId}
      </div>

      {/* Optional gradient overlay for readability */}
      <div className="absolute top-0 left-0 w-full h-12 bg-gradient-to-b from-black/70 to-transparent z-0" />

      <video
        ref={videoRef}
        autoPlay
        muted
        playsInline
        controls={false}
        className="w-full h-full object-contain"
      />
    </div>
  );
}