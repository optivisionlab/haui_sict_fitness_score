import ProtectedRoute from "@/components/protected-route";
import { ReactNode } from "react";

export default function StudentPage({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={["student"]}>
      <div className="bg-[#eeeeee] h-[calc(100vh-var(--navHeight))]">
        {children}
      </div>
    </ProtectedRoute>
  );
}
