import { Injectable, signal, computed } from '@angular/core';
import {
  AdminStudentItem,
  AdminCourseClass,
  AdminDashboardKpi,
  ExamConditionType
} from '../models/admin.model';

@Injectable({
  providedIn: 'root'
})
export class AdminDataService {
  // Mock classes list
  readonly classes = signal<AdminCourseClass[]>([
    {
      id: 'cls-1',
      subjectName: 'Rèn luyện Thể lực & Chạy cự ly',
      subjectCode: 'FIT101',
      classCode: '20261_FIT101_01',
      teacher: 'ThS. Nguyễn Văn Cường',
      startDate: '10/08/2026',
      endDate: '15/10/2026',
      regularGradeDeadline: '05/10/2026',
      totalStudents: 45,
      eligibleCount: 41,
      status: 'ongoing'
    },
    {
      id: 'cls-2',
      subjectName: 'Kỹ thuật & Chiến thuật Pickleball',
      subjectCode: 'FIT102',
      classCode: '20261_FIT102_02',
      teacher: 'TS. Trần Đình Dũng',
      startDate: '12/08/2026',
      endDate: '20/10/2026',
      regularGradeDeadline: '10/10/2026',
      totalStudents: 38,
      eligibleCount: 32,
      status: 'ongoing'
    },
    {
      id: 'cls-3',
      subjectName: 'Thể hình & Phát triển Thể chất',
      subjectCode: 'FIT103',
      classCode: '20261_FIT103_01',
      teacher: 'ThS. Hoàng Minh Đức',
      startDate: '01/06/2026',
      endDate: '15/08/2026',
      regularGradeDeadline: '05/08/2026',
      totalStudents: 40,
      eligibleCount: 37,
      status: 'completed'
    },
    {
      id: 'cls-4',
      subjectName: 'Điền kinh cơ bản & Nhảy cao',
      subjectCode: 'FIT104',
      classCode: '20261_FIT104_03',
      teacher: 'ThS. Lê Thanh Hải',
      startDate: '15/08/2026',
      endDate: '30/10/2026',
      regularGradeDeadline: '20/10/2026',
      totalStudents: 42,
      eligibleCount: 35,
      status: 'ongoing'
    },
    {
      id: 'cls-5',
      subjectName: 'Bóng bàn căn bản & Phản xạ',
      subjectCode: 'FIT105',
      classCode: '20261_FIT105_02',
      teacher: 'ThS. Vũ Hoàng Lan',
      startDate: '20/08/2026',
      endDate: '05/11/2026',
      regularGradeDeadline: '25/10/2026',
      totalStudents: 35,
      eligibleCount: 33,
      status: 'ongoing'
    },
    {
      id: 'cls-6',
      subjectName: 'Bơi lội & Kỹ năng cứu đuối',
      subjectCode: 'FIT106',
      classCode: '20261_FIT106_01',
      teacher: 'ThS. Phạm Quốc Tuấn',
      startDate: '01/06/2026',
      endDate: '20/08/2026',
      regularGradeDeadline: '10/08/2026',
      totalStudents: 30,
      eligibleCount: 29,
      status: 'completed'
    }
  ]);

  // Mock students list
  readonly students = signal<AdminStudentItem[]>([
    {
      id: 'stu-1',
      studentCode: '2026601001',
      fullName: 'Nguyễn Văn An',
      majorClass: 'KTPM01 - K17',
      subjectName: 'Rèn luyện Thể lực & Chạy cự ly',
      classCode: '20261_FIT101_01',
      startDate: '10/08/2026',
      regularGradeDeadline: '05/10/2026',
      liveClassCompleted: 4,
      liveClassTotal: 4,
      practiceCompleted: 30,
      practiceTotal: 30,
      testCompleted: 2,
      testTotal: 2,
      examCondition: 'eligible',
      finalScore: 8.8,
      weeklyDetails: [
        { week: 'Tuần 1', period: '10/08 - 16/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '17/08 - 23/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '24/08 - 30/08', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '31/08 - 06/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '07/09 - 13/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 6', period: '14/09 - 20/09', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 7', period: '21/09 - 27/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-2',
      studentCode: '2026601045',
      fullName: 'Trần Thị Mai',
      majorClass: 'HTTT02 - K17',
      subjectName: 'Kỹ thuật & Chiến thuật Pickleball',
      classCode: '20261_FIT102_02',
      startDate: '12/08/2026',
      regularGradeDeadline: '10/10/2026',
      liveClassCompleted: 3,
      liveClassTotal: 4,
      practiceCompleted: 26,
      practiceTotal: 30,
      testCompleted: 2,
      testTotal: 2,
      examCondition: 'eligible',
      finalScore: 8.2,
      weeklyDetails: [
        { week: 'Tuần 1', period: '12/08 - 18/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '19/08 - 25/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '26/08 - 01/09', practiceCompleted: 3, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '02/09 - 08/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '09/09 - 15/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 6', period: '16/09 - 22/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-3',
      studentCode: '2026601112',
      fullName: 'Lê Hoàng Nam',
      majorClass: 'CNTT03 - K17',
      subjectName: 'Rèn luyện Thể lực & Chạy cự ly',
      classCode: '20261_FIT101_01',
      startDate: '10/08/2026',
      regularGradeDeadline: '05/10/2026',
      liveClassCompleted: 1,
      liveClassTotal: 4,
      practiceCompleted: 12,
      practiceTotal: 30,
      testCompleted: 0,
      testTotal: 2,
      examCondition: 'ineligible',
      examConditionNote: 'Chưa đủ số bài luyện tập tối thiểu và thiếu bài kiểm tra định kỳ',
      finalScore: 4.0,
      weeklyDetails: [
        { week: 'Tuần 1', period: '10/08 - 16/08', practiceCompleted: 3, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '17/08 - 23/08', practiceCompleted: 2, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Cần bổ sung' },
        { week: 'Tuần 3', period: '24/08 - 30/08', practiceCompleted: 3, liveClassCompleted: 0, testCompleted: 0, examCondition: 'Không đạt' },
        { week: 'Tuần 4', period: '31/08 - 06/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Cần bổ sung' }
      ]
    },
    {
      id: 'stu-4',
      studentCode: '2026601288',
      fullName: 'Phạm Đức Long',
      majorClass: 'KHMT01 - K17',
      subjectName: 'Kỹ thuật & Chiến thuật Pickleball',
      classCode: '20261_FIT102_02',
      startDate: '12/08/2026',
      regularGradeDeadline: '10/10/2026',
      liveClassCompleted: 2,
      liveClassTotal: 4,
      practiceCompleted: 20,
      practiceTotal: 30,
      testCompleted: 1,
      testTotal: 2,
      examCondition: 'pending',
      examConditionNote: 'Cần nộp bù 01 video kỹ thuật giao bóng trước ngày 08/10',
      finalScore: 6.5,
      weeklyDetails: [
        { week: 'Tuần 1', period: '12/08 - 18/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '19/08 - 25/08', practiceCompleted: 3, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Cần bổ sung' },
        { week: 'Tuần 3', period: '26/08 - 01/09', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '02/09 - 08/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '09/09 - 15/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-5',
      studentCode: '2026601334',
      fullName: 'Vũ Thùy Linh',
      majorClass: 'ATTT01 - K17',
      subjectName: 'Điền kinh cơ bản & Nhảy cao',
      classCode: '20261_FIT104_03',
      startDate: '15/08/2026',
      regularGradeDeadline: '20/10/2026',
      liveClassCompleted: 4,
      liveClassTotal: 4,
      practiceCompleted: 28,
      practiceTotal: 28,
      testCompleted: 2,
      testTotal: 2,
      examCondition: 'eligible',
      finalScore: 9.2,
      weeklyDetails: [
        { week: 'Tuần 1', period: '15/08 - 21/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '22/08 - 28/08', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '29/08 - 04/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '05/09 - 11/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '12/09 - 18/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 6', period: '19/09 - 25/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-6',
      studentCode: '2026601402',
      fullName: 'Đỗ Hữu Thắng',
      majorClass: 'KTPM02 - K17',
      subjectName: 'Rèn luyện Thể lực & Chạy cự ly',
      classCode: '20261_FIT101_01',
      startDate: '10/08/2026',
      regularGradeDeadline: '05/10/2026',
      liveClassCompleted: 3,
      liveClassTotal: 4,
      practiceCompleted: 28,
      practiceTotal: 30,
      testCompleted: 2,
      testTotal: 2,
      examCondition: 'eligible',
      finalScore: 8.0,
      weeklyDetails: [
        { week: 'Tuần 1', period: '10/08 - 16/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '17/08 - 23/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '24/08 - 30/08', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '31/08 - 06/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '07/09 - 13/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 6', period: '14/09 - 20/09', practiceCompleted: 6, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-7',
      studentCode: '2026601456',
      fullName: 'Bùi Lan Hương',
      majorClass: 'HTTT01 - K17',
      subjectName: 'Bóng bàn căn bản & Phản xạ',
      classCode: '20261_FIT105_02',
      startDate: '20/08/2026',
      regularGradeDeadline: '25/10/2026',
      liveClassCompleted: 2,
      liveClassTotal: 3,
      practiceCompleted: 22,
      practiceTotal: 25,
      testCompleted: 1,
      testTotal: 2,
      examCondition: 'pending',
      examConditionNote: 'Đang theo dõi hoàn thành bài thi số 2',
      finalScore: 7.0,
      weeklyDetails: [
        { week: 'Tuần 1', period: '20/08 - 26/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '27/08 - 02/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '03/09 - 09/09', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '10/09 - 16/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '17/09 - 23/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-8',
      studentCode: '2026601511',
      fullName: 'Hoàng Quốc Việt',
      majorClass: 'KHMT02 - K17',
      subjectName: 'Rèn luyện Thể lực & Chạy cự ly',
      classCode: '20261_FIT101_01',
      startDate: '10/08/2026',
      regularGradeDeadline: '05/10/2026',
      liveClassCompleted: 1,
      liveClassTotal: 4,
      practiceCompleted: 10,
      practiceTotal: 30,
      testCompleted: 0,
      testTotal: 2,
      examCondition: 'ineligible',
      examConditionNote: 'Nghỉ quá số buổi LiveClass quy định (chỉ tham gia 1/4 buổi)',
      finalScore: 3.5,
      weeklyDetails: [
        { week: 'Tuần 1', period: '10/08 - 16/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '17/08 - 23/08', practiceCompleted: 3, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Cần bổ sung' },
        { week: 'Tuần 3', period: '24/08 - 30/08', practiceCompleted: 3, liveClassCompleted: 0, testCompleted: 0, examCondition: 'Không đạt' }
      ]
    },
    {
      id: 'stu-9',
      studentCode: '2026601599',
      fullName: 'Ngô Mỹ Duyên',
      majorClass: 'KTPM03 - K17',
      subjectName: 'Kỹ thuật & Chiến thuật Pickleball',
      classCode: '20261_FIT102_02',
      startDate: '12/08/2026',
      regularGradeDeadline: '10/10/2026',
      liveClassCompleted: 4,
      liveClassTotal: 4,
      practiceCompleted: 30,
      practiceTotal: 30,
      testCompleted: 2,
      testTotal: 2,
      examCondition: 'eligible',
      finalScore: 9.5,
      weeklyDetails: [
        { week: 'Tuần 1', period: '12/08 - 18/08', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '19/08 - 25/08', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '26/08 - 01/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '02/09 - 08/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '09/09 - 15/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 6', period: '16/09 - 22/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: 1, examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-10',
      studentCode: '2026601672',
      fullName: 'Đinh Công Trình',
      majorClass: 'ATTT02 - K17',
      subjectName: 'Bóng bàn căn bản & Phản xạ',
      classCode: '20261_FIT105_02',
      startDate: '20/08/2026',
      regularGradeDeadline: '25/10/2026',
      liveClassCompleted: 3,
      liveClassTotal: 3,
      practiceCompleted: 24,
      practiceTotal: 25,
      testCompleted: 2,
      testTotal: 2,
      examCondition: 'eligible',
      finalScore: 8.5,
      weeklyDetails: [
        { week: 'Tuần 1', period: '20/08 - 26/08', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '27/08 - 02/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '03/09 - 09/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '10/09 - 16/09', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '17/09 - 23/09', practiceCompleted: 5, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-11',
      studentCode: '2026601720',
      fullName: 'Dương Thị Yến',
      majorClass: 'KTPM01 - K17',
      subjectName: 'Điền kinh cơ bản & Nhảy cao',
      classCode: '20261_FIT104_03',
      startDate: '15/08/2026',
      regularGradeDeadline: '20/10/2026',
      liveClassCompleted: 3,
      liveClassTotal: 4,
      practiceCompleted: 25,
      practiceTotal: 28,
      testCompleted: 2,
      testTotal: 2,
      examCondition: 'eligible',
      finalScore: 8.0,
      weeklyDetails: [
        { week: 'Tuần 1', period: '15/08 - 21/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '22/08 - 28/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 3', period: '29/08 - 04/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '05/09 - 11/09', practiceCompleted: 5, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '12/09 - 18/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 6', period: '19/09 - 25/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' }
      ]
    },
    {
      id: 'stu-12',
      studentCode: '2026601888',
      fullName: 'Phan Tuấn Kiệt',
      majorClass: 'HTTT02 - K17',
      subjectName: 'Rèn luyện Thể lực & Chạy cự ly',
      classCode: '20261_FIT101_01',
      startDate: '10/08/2026',
      regularGradeDeadline: '05/10/2026',
      liveClassCompleted: 2,
      liveClassTotal: 4,
      practiceCompleted: 18,
      practiceTotal: 30,
      testCompleted: 1,
      testTotal: 2,
      examCondition: 'pending',
      examConditionNote: 'Cần bổ sung 4 bài chạy GPS trước hạn chốt',
      finalScore: 6.0,
      weeklyDetails: [
        { week: 'Tuần 1', period: '10/08 - 16/08', practiceCompleted: 4, liveClassCompleted: 1, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 2', period: '17/08 - 23/08', practiceCompleted: 3, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Cần bổ sung' },
        { week: 'Tuần 3', period: '24/08 - 30/08', practiceCompleted: 3, liveClassCompleted: 1, testCompleted: 1, examCondition: 'Đạt' },
        { week: 'Tuần 4', period: '31/08 - 06/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Đạt' },
        { week: 'Tuần 5', period: '07/09 - 13/09', practiceCompleted: 4, liveClassCompleted: 0, testCompleted: '-', examCondition: 'Cần bổ sung' }
      ]
    }
  ]);

  // Computed KPIs
  readonly kpis = computed<AdminDashboardKpi>(() => {
    const list = this.students();
    const total = list.length;
    const eligible = list.filter((s) => s.examCondition === 'eligible').length;
    const pending = list.filter((s) => s.examCondition === 'pending' || s.examCondition === 'ineligible').length;
    const rate = total > 0 ? Math.round((eligible / total) * 100) : 0;

    return {
      totalStudents: total,
      totalClasses: this.classes().length,
      eligibleRate: rate,
      pendingReviewCount: pending
    };
  });

  // Update student exam condition
  updateExamCondition(studentId: string, condition: ExamConditionType, note?: string): void {
    this.students.update((prev) =>
      prev.map((item) => {
        if (item.id === studentId) {
          return {
            ...item,
            examCondition: condition,
            examConditionNote: note ?? item.examConditionNote
          };
        }
        return item;
      })
    );
  }
}
