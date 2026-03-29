"use client";

import { useEffect, useRef } from "react";
import Hls from "hls.js";

export function CameraBox({
  camId,
}: {
  camId: number;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!videoRef.current) return;

    const video = videoRef.current;

    // URL HLS đúng từ MediaMTX
    const url = `http://10.1.12.88:8888/cam${camId}/video1_stream.m3u8`;

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
    <div className="bg-black rounded-xl overflow-hidden aspect-video flex items-center justify-center">
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