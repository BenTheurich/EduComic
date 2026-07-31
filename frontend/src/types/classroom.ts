import { Student } from './student';

export interface Classroom {
  id: string;
  name: string;
  subject: string;
  grade_level: string;
  story_theme: string;
  design_style: 'manga' | 'comic' | 'cartoon';
  duration: string;
  created_at: string;
}

export interface ClassroomWithStudents extends Classroom {
  students: Student[];
  student_count: number;
  story_count: number;
}

export interface Chapter {
  id: string;
  classroom_id: string;
  index: number;
  chapter_outline: string;
  original_prompt: string;
  thumbnail_url: string | null;
  story_title: string;
  status: string;
  created_at: string;
}
