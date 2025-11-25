"use client";

import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Legend,
  ResponsiveContainer,
} from "recharts";

export interface ScoreData {
  name: string;
  uv: number;
  pv?: number;
  amt?: number;
}

interface ChartScoreProps {
  title?: string;
  data: ScoreData[];
  height?: number; // Chiều cao có thể tùy chỉnh
}

const ChartScore: React.FC<ChartScoreProps> = ({
  title = "Điểm (Trên thang 4)",
  data,
  height = 250,
}) => {
  return (
    <div>
      <h1 className="text-xl font-semibold mb-3">{title}</h1>

      <div style={{ width: "100%", height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 5, right: 20, bottom: 5, left: 0 }}
          >
            <CartesianGrid stroke="#aaa" strokeDasharray="5 5" />
            <Line
              type="monotone"
              dataKey="uv"
              stroke="purple"
              strokeWidth={2}
              name="Điểm số qua mỗi lần kiểm tra"
            />
            <XAxis dataKey="name" />
            <YAxis />
            <Legend align="right" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ChartScore;
