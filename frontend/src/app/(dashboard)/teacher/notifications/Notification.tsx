"use client";

import "./Notification.scss";

interface Type {
  id: number;
  infor: String;
  time: number;
}

const Notification = ({ id, infor, time }: Type) => {
  return (
    <div className="card w-full mt-[var(--distanceAll)] px-[20px]">
      <div className="container">
        <div className="left">
          <div className="status-ind"></div>
        </div>
        <div className="right">
          <div className="text-wrap">
            <p className="text-content">{infor}</p>
            <p className="time">{time}h trước</p>
          </div>
          <div className="button-wrap">
            <button className="primary-cta">Bấm vào để xem chi tiết</button>
            {/* <button className="secondary-cta">Mark as read</button> */}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Notification;
