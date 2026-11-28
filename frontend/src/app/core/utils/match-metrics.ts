/**
 * Hiển thị metrics AI trả về: nhãn tiếng Việt cho chỉ số và danh sách cú đánh
 * của bài quay đối kháng (metrics.events, công thức 14 của đề án).
 */

const METRIC_LABELS: Record<string, string> = {
  accuracy: 'Tỷ lệ trúng',
  hitCount: 'Số lần trúng',
  missCount: 'Số lần trượt',
  swingTotal: 'Tổng số cú',
  inCourtCount: 'Trúng nảy trong sân',
  calibration: 'Sân',
  ballSeenRatio: 'Tỷ lệ khung thấy bóng'
};

const CALIBRATION_LABELS: Record<string, string> = {
  court: 'đã đánh dấu',
  auto: 'AI tự ước lượng lưới',
  fallback: 'không ước lượng được lưới'
};

const REASON_LABELS: Record<string, string> = {
  in_zone: 'nảy trong vùng đích',
  returned: 'đối phương đỡ được',
  crossed_no_bounce: 'qua lưới, không thấy điểm nảy',
  net: 'không qua lưới',
  out_of_zone: 'nảy ngoài vùng đích',
  no_cross: 'không thấy bóng qua lưới'
};

export interface MetricChip {
  key: string;
  label: string;
  value: string;
}

export interface ShotEvent {
  time: number;
  timeText: string;
  hit: boolean;
  reason: string;
}

function percent(v: number): string {
  return `${Math.round(v * 1000) / 10}%`;
}

/** Chỉ số dạng thẻ (bỏ danh sách cú đánh và giá trị dạng object). */
export function metricChips(metrics: Record<string, any> | null | undefined): MetricChip[] {
  if (!metrics) return [];
  return Object.keys(metrics)
    .filter(k => k !== 'events' && metrics[k] !== null && typeof metrics[k] !== 'object')
    .map(k => {
      const v = metrics[k];
      let value = String(v);
      if ((k === 'accuracy' || k === 'ballSeenRatio') && typeof v === 'number') value = percent(v);
      if (k === 'calibration') value = CALIBRATION_LABELS[v] || String(v);
      return { key: k, label: METRIC_LABELS[k] || k, value };
    });
}

/** Danh sách cú đánh của bài đối kháng, theo thời gian. */
export function shotEvents(metrics: Record<string, any> | null | undefined): ShotEvent[] {
  const events = metrics?.['events'];
  if (!Array.isArray(events)) return [];
  return events
    .filter(e => e && typeof e.time === 'number')
    .map(e => {
      const m = Math.floor(e.time / 60);
      const s = (e.time % 60).toFixed(1).padStart(4, '0');
      return {
        time: e.time,
        timeText: `${m}:${s}`,
        hit: e.result === 'hit',
        reason: REASON_LABELS[e.reason] || e.reason || ''
      };
    });
}
