import { CheckinEvent } from "@/app/(dashboard)/admin/demo/page";

export function UserCard({ user }: { user: CheckinEvent }) {
  return (
    <div className="rounded-xl border bg-white p-3 shadow-sm hover:shadow transition">
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-sm">👤 User #{user.user_id}</span>
        <span className="text-xs text-gray-500">CAM {user.last_cam}</span>
      </div>

      <div className="text-xs text-gray-600 space-y-1">
        <p>
          <span className="font-medium">User name:</span> {user.user_name}
        </p>
        <p>
          <span className="font-medium">Step:</span> {user.step}
        </p>
        <p>
          <span className="font-medium">Lap:</span> {user.lap}
        </p>
        <p>
          <span className="font-medium">Start:</span> {user.start_time}
        </p>
        <p>
          <span className="font-medium">Last:</span> {user.last_time}
        </p>
      </div>
    </div>
  );
}
