"use client";

import React, { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { toast } from "sonner";
import { ScoreTableType } from "@/types/scoreTableType";

const Page = () => {
  const { get, post } = useApi();
  const [classes, setClasses] = useState([]);
  const [exams, setExams] = useState([]);

  const [selectedClass, setSelectedClass] = useState("");
  const [selectedExam, setSelectedExam] = useState("");

  const [results, setResults] = useState<ScoreTableType[]>([]);

  // fetch Class & Exam
  const fetchClasses = async () => {
    const data = await get("/class");
    console.log(data);
    setClasses(data);
  };

  const fetchExams = async (classId: number) => {
    const data = await get(`/class/${classId}/exams`);
    console.log(data.items);
    setExams(data.items);
  };

  // --- Giả sử API load danh sách ---
  useEffect(() => {
    fetchClasses();
  }, []);

  const fetchResults = async () => {
    if (!selectedClass || !selectedExam) return;

    try {
      const data = await get(
        `/class/${selectedClass}/exam/${selectedExam}/results/by-user/top`
      );

      setResults(data.items);
      console.log(data.items);
    } catch (err: any) {
      toast.error(err);
    }
  };

  // Fetch khi chọn đủ 2 select
  useEffect(() => {
    if (selectedClass && selectedExam) {
      fetchResults();
    }
  }, [selectedClass, selectedExam]);

  return (
    <div className="p-12 space-y-6">
      <h2 className="text-xl font-bold">
        Xem kết quả bài kiểm tra theo lớp & bài thi
      </h2>

      {/* Select Container */}
      <div className="flex gap-4">
        {/* Select Class */}
        <select
          value={selectedClass}
          onChange={(e) => {
            const classHas = e.target.value;
            setSelectedClass(classHas);
            // reset exam & results
            setSelectedExam("");
            setExams([]);
            setResults([]);

            if (classHas) {
              fetchExams(Number(e.target.value));
            }
          }}
          className="border p-2 rounded w-48"
        >
          <option value="">-- Chọn lớp học --</option>
          {classes.map((c: any) => (
            <option key={c.class_id} value={c.class_id}>
              {c.class_name}
            </option>
          ))}
        </select>

        {/* Select Exam */}
        <select
          value={selectedExam}
          onChange={(e) => {
            setSelectedExam(e.target.value);
            console.log(exams);
          }}
          className="border p-2 rounded w-48"
        >
          <option value="">-- Chọn bài thi --</option>
          {exams.map((e: any) => (
            <option key={e.exam_id} value={e.exam_id}>
              {e.title}
            </option>
          ))}
        </select>
      </div>

      {/* Results */}
      <div className="mt-6">
        <h3 className="text-lg font-semibold">Kết quả:</h3>

        {results.length === 0 && <p>Chưa có dữ liệu.</p>}

        <ul className="space-y-3">
          {results.map((item: any) => (
            <li
              key={item.user.user_id}
              className="border p-4 rounded shadow-sm bg-white"
            >
              <p>
                <strong>User:</strong> {item.user.full_name}(
                {item.user.user_name})
              </p>
              <p>
                <strong>Email:</strong> {item.user.email}
              </p>
              <p>
                <strong>User Code:</strong> {item.user.user_code}
              </p>

              <hr className="my-2" />

              {item.result ? (
                <>
                  <p>Result ID: {item.result.result_id}</p>
                  <p>Step: {item.result.step}</p>
                  <p>
                    Thời gian: {item.result.start_time} → {item.result.end_time}
                  </p>
                  <p>Avg Speed: {item.result.avg_speed}</p>
                </>
              ) : (
                <p>Chưa có kết quả</p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default Page;
