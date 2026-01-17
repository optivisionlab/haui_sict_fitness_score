// Hàm nhận vào startTime và endTime phía be -> xử lý tách
export function calcRunInfo(start: string, end: string) {
  if (!start || !end) {
    return {
      date: "-",
      start: "-",
      end: "-",
      duration: "-",
    };
  }

  const startDate = new Date(start);
  const endDate = new Date(end);

  const date = startDate.toLocaleDateString("vi-VN");
  const startTime = startDate.toLocaleTimeString("vi-VN");
  const endTime = endDate.toLocaleTimeString("vi-VN");

  const ms = endDate.getTime() - startDate.getTime();
  if (ms <= 0) {
    return { date, start: startTime, end: endTime, duration: "0s" };
  }

  const totalSec = Math.floor(ms / 1000);

  const hours = Math.floor(totalSec / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;

  let duration = "";
  if (hours > 0) duration = `${hours}h ${minutes}m ${seconds}s`;
  else if (minutes > 0) duration = `${minutes}m ${seconds}s`;
  else duration = `${seconds}s`;

  return {
    date,
    start: startTime,
    end: endTime,
    duration,
  };
}
