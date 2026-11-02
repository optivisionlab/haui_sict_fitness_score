export type PhysicalSubjectCode =
  | 'PICKLEBALL'
  | 'RUNNING'
  | 'FOOTBALL'
  | 'BADMINTON'
  | 'BASKETBALL'
  | 'VOLLEYBALL'
  | 'SWIMMING'
  | 'GENERAL';

export interface PhysicalSubjectMeta {
  code: PhysicalSubjectCode;
  name: string;
  coursePrefix: string;
  defaultMode: 'video' | 'camera';
}

export const PHYSICAL_SUBJECTS: PhysicalSubjectMeta[] = [
  { code: 'PICKLEBALL', name: 'Pickleball', coursePrefix: 'GDTC-PB', defaultMode: 'video' },
  { code: 'RUNNING', name: 'Điền kinh', coursePrefix: 'GDTC-CB', defaultMode: 'camera' },
  { code: 'FOOTBALL', name: 'Bóng đá', coursePrefix: 'GDTC-FB', defaultMode: 'video' },
  { code: 'BADMINTON', name: 'Cầu lông', coursePrefix: 'GDTC-CL', defaultMode: 'video' },
  { code: 'BASKETBALL', name: 'Bóng rổ', coursePrefix: 'GDTC-BR', defaultMode: 'video' },
  { code: 'VOLLEYBALL', name: 'Bóng chuyền', coursePrefix: 'GDTC-BC', defaultMode: 'video' },
  { code: 'SWIMMING', name: 'Bơi lội', coursePrefix: 'GDTC-BL', defaultMode: 'video' },
  { code: 'GENERAL', name: 'Giáo dục Thể chất', coursePrefix: 'GDTC', defaultMode: 'video' }
];

export const PHYSICAL_SUBJECTS_MAP: Record<PhysicalSubjectCode, PhysicalSubjectMeta> =
  PHYSICAL_SUBJECTS.reduce((acc, curr) => {
    acc[curr.code] = curr;
    return acc;
  }, {} as Record<PhysicalSubjectCode, PhysicalSubjectMeta>);

export interface ParsedSemester {
  code: string;
  name: string;
  academicYear: string;
  term: number;
}

export function parseSemesterCode(raw?: string | null): ParsedSemester {
  if (!raw || typeof raw !== 'string') {
    return {
      code: '2026-2027.1',
      name: 'Học kỳ 1 (2026 - 2027)',
      academicYear: '2026-2027',
      term: 1
    };
  }

  const s = raw.trim();
  if (s.includes('.')) {
    const [year, termStr] = s.split('.');
    const term = parseInt(termStr, 10) || 1;
    const termLabels: Record<number, string> = {
      1: 'Học kỳ 1',
      2: 'Học kỳ 2',
      3: 'Học kỳ hè'
    };
    const termText = termLabels[term] || `Học kỳ ${term}`;
    const cleanYear = year.replace(' - ', '-');
    return {
      code: s,
      name: `${termText} (${cleanYear.replace('-', ' - ')})`,
      academicYear: cleanYear,
      term
    };
  }

  return {
    code: s,
    name: `Học kỳ (${s})`,
    academicYear: s,
    term: 1
  };
}

export function deduceSportMetadata(name: string = '', code: string = ''): PhysicalSubjectMeta {
  const nl = (name || '').toLowerCase();
  const cl = (code || '').toLowerCase();
  if (nl.includes('pickleball') || cl.includes('pb')) {
    return PHYSICAL_SUBJECTS_MAP['PICKLEBALL'];
  }
  if (nl.includes('điền kinh') || nl.includes('chạy') || cl.includes('run') || cl.includes('cb')) {
    return PHYSICAL_SUBJECTS_MAP['RUNNING'];
  }
  if (nl.includes('bóng đá') || nl.includes('đá bóng') || cl.includes('fb') || cl.includes('foot')) {
    return PHYSICAL_SUBJECTS_MAP['FOOTBALL'];
  }
  if (nl.includes('cầu lông') || cl.includes('badminton') || cl.includes('cl')) {
    return PHYSICAL_SUBJECTS_MAP['BADMINTON'];
  }
  if (nl.includes('bóng rổ') || cl.includes('basket') || cl.includes('br')) {
    return PHYSICAL_SUBJECTS_MAP['BASKETBALL'];
  }
  if (nl.includes('bóng chuyền') || cl.includes('volley') || cl.includes('bc')) {
    return PHYSICAL_SUBJECTS_MAP['VOLLEYBALL'];
  }
  if (nl.includes('bơi') || cl.includes('swim') || cl.includes('bl')) {
    return PHYSICAL_SUBJECTS_MAP['SWIMMING'];
  }
  return PHYSICAL_SUBJECTS_MAP['GENERAL'];
}
