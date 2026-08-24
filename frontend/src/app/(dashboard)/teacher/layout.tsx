import ProtectedRoute from "@/components/protected-route";

import { ReactNode } from "react";
const TeacherPage = ({ children }: { children: ReactNode }) => {
  return (
    <>
      <ProtectedRoute allowedRoles={["teacher"]}>
        <div className="bg-[#eeeeee] h-[calc(100vh-var(--navHeight))]">
          {children}
        </div>
      </ProtectedRoute>
    </>
  );
};

export default TeacherPage;
