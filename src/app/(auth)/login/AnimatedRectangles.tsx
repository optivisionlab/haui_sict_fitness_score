"use client";

import { motion } from "framer-motion";

const rects = [
  {
    className: "w-64 h-40 bg-blue-300/60 rounded-[32px]",
    x: -80,
    y: -60,
    duration: 14,
  },
  {
    className: "w-48 h-28 bg-pink-300/60 rounded-3xl",
    x: 90,
    y: -40,
    duration: 12,
  },
  {
    className: "w-36 h-24 bg-purple-300/60 rounded-2xl",
    x: -40,
    y: 80,
    duration: 10,
  },
  {
    className: "w-72 h-44 bg-emerald-300/50 rounded-[40px]",
    x: 60,
    y: 60,
    duration: 18,
  },
];

export default function AnimatedRectangles() {
  return (
    <div className="relative w-full h-full overflow-hidden bg-muted flex items-center justify-center">
      {rects.map((r, i) => (
        <motion.div
          key={i}
          className={`absolute ${r.className}`}
          animate={{
            x: [0, r.x, 0],
            y: [0, r.y, 0],
            rotate: [0, 8, 0],
          }}
          transition={{
            duration: r.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}

      {/* Content giữa */}
      <div className="relative z-10 text-center">
        <h2 className="text-3xl font-bold text-gray-700 dark:text-gray-200">
          Chào mừng bạn đến với Fitness-Score ✨
        </h2>
        <p className="mt-2 text-sm text-gray-500">
          Đăng nhập để tiếp tục học tập
        </p>
      </div>
    </div>
  );
}
