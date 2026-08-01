/**
 * API client configuration and utilities
 */
import type { Chapter, ChapterPreview, ChapterStatus, ChapterWithPanels } from "@/types/story";
import type { Student } from "@/types/student";

const API_BASE_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.DEV || import.meta.env.MODE === 'test'
    ? 'http://127.0.0.1:8000'
    : (() => { throw new Error('VITE_API_URL must be set for production builds.'); })()
);

/**
 * Base fetch wrapper with error handling
 */
export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const headers: HeadersInit = { ...options?.headers };

    // Only add Content-Type if not already set and if there's a body
    if (!headers['Content-Type'] && options?.body && typeof options.body === 'string') {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Network error occurred');
  }
}

/**
 * API client object with all endpoints
 */
export const api = {
  // Health check
  health: () => apiFetch<{ status: string }>('/health'),

  // Classrooms
  classrooms: {
    create: (data: {
      name: string;
      subject: string;
      grade_level: string;
      story_theme: string;
      design_style: string;
    }) =>
      apiFetch<{
        success: boolean;
        classroom: {
          id: string;
          name: string;
          subject: string;
          grade_level: string;
          story_theme: string;
          design_style: string;
          created_at: string;
        };
      }>(
        '/classrooms',
        {
          method: 'POST',
          body: JSON.stringify(data),
        }
      ),

    getAll: () =>
      apiFetch<{
        success: boolean;
        classrooms: Array<{
          id: string;
          name: string;
          subject: string;
          grade_level: string;
          story_theme: string;
          design_style: string;
          student_count: number;
          story_count: number;
          created_at: string;
        }>;
      }>('/classrooms'),

    getById: (classroomId: string) =>
      apiFetch<{
        success: boolean;
        classroom: {
          id: string;
          name: string;
          subject: string;
          grade_level: string;
          story_theme: string;
          design_style: string;
          created_at: string;
          students: Array<{
            id: string;
            name: string;
            interests: string;
            avatar_url: string | null;
            created_at: string;
          }>;
        };
      }>(`/classrooms/${classroomId}`),

    getStudents: (classroomId: string) =>
      apiFetch<{
        success: boolean;
        students: Array<{
          id: string;
          name: string;
          interests: string;
          avatar_url: string | null;
          created_at: string;
        }>;
      }>(`/classrooms/${classroomId}/students`),

    getChapters: (classroomId: string) =>
      apiFetch<{
        success: boolean;
        chapters: Chapter[];
      }>(`/classrooms/${classroomId}/chapters`),

    update: (classroomId: string, data: { name: string; subject: string; grade_level: string; story_theme: string; design_style: string }) =>
      apiFetch<{ success: boolean }>(`/classrooms/${classroomId}`, { method: 'PATCH', body: JSON.stringify(data) }),

    delete: (classroomId: string) =>
      apiFetch<{ success: boolean }>(`/classrooms/${classroomId}?confirm=true`, { method: 'DELETE' }),

  },

  // Story generation
  story: {
    startChapter: (classroomId: string, lessonPrompt: string) =>
      apiFetch<{
        success: boolean;
        chapter: Chapter & {
          story_ideas: Array<{
            id: string;
            title: string;
            summary: string;
            theme: string;
          }>;
          chosen_idea_id: string | null;
        };
      }>(`/classrooms/${classroomId}/chapters/start`, {
        method: 'POST',
        body: JSON.stringify({ lesson_prompt: lessonPrompt }),
      }),

    chooseIdea: (chapterId: string, ideaId: string) =>
      apiFetch<{
        success: boolean;
        chapter: Chapter;
      }>(`/chapters/${chapterId}/choose-idea`, {
        method: 'POST',
        body: JSON.stringify({ idea_id: ideaId }),
      }),

    commitChapter: (chapterId: string, ideaId: string, idempotencyKey: string) =>
      apiFetch<{
        success: boolean;
        message: string;
        chapter_id: string;
        status: ChapterStatus;
      }>('/chapters/commit', {
        method: 'POST',
        body: JSON.stringify({
          chapter_id: chapterId,
          chosen_idea_id: ideaId,
          idempotency_key: idempotencyKey,
        }),
      }),
  },

  // Avatar generation
  avatar: {
    create: (studentId: string) =>
      apiFetch<{
        success: boolean;
        student: Student;
      }>(`/avatar/create/${studentId}`, {
        method: 'POST',
      }),
  },

  // Students
  students: {
    getAll: () =>
      apiFetch<{
        success: boolean;
        students: Array<{
          id: string;
          name: string;
          interests: string;
          avatar_url: string | null;
          created_at: string;
        }>;
      }>('/students'),

    create: (name: string, interests: string, classroomId?: string, studentId?: string) =>
      apiFetch<{
        success: boolean;
        student: {
          id: string;
          name: string;
          interests: string;
          avatar_url: string | null;
          created_at: string;
        };
      }>('/students/create', {
        method: 'POST',
        body: JSON.stringify({ name, interests, classroom_id: classroomId, student_id: studentId }),
      }),

    joinClassroom: (studentId: string, classroomId: string) =>
      apiFetch<{
        success: boolean;
        message: string;
        student: {
          id: string;
          name: string;
          interests: string;
          avatar_url: string | null;
          created_at: string;
        };
        classroom: {
          id: string;
          name: string;
          subject: string;
          grade_level: string;
          story_theme: string;
        };
      }>(`/students/${studentId}/join-classroom/${classroomId}`, {
        method: 'POST',
      }),

    getById: (studentId: string) =>
      apiFetch<{
        success: boolean;
        student: {
          id: string;
          name: string;
          interests: string;
          avatar_url: string | null;
          created_at: string;
        };
        classrooms: Array<{
          id: string;
          name: string;
          subject: string;
          grade_level: string;
          story_theme: string;
          design_style: string;
          created_at: string;
        }>;
      }>(`/students/${studentId}`),

    getClassrooms: (studentId: string) =>
      apiFetch<{
        success: boolean;
        classrooms: Array<{
          id: string;
          name: string;
          subject: string;
          grade_level: string;
          story_theme: string;
          design_style: string;
          created_at: string;
        }>;
      }>(`/students/${studentId}/classrooms`),

    getChapters: (studentId: string) =>
      apiFetch<{
        success: boolean;
        chapters: ChapterPreview[];
      }>(`/students/${studentId}/chapters`),

    leaveClassroom: (studentId: string, classroomId: string) =>
      apiFetch<{
        success: boolean;
        message: string;
      }>(`/students/${studentId}/leave-classroom/${classroomId}?confirm=true`, {
        method: 'DELETE',
      }),

    update: (studentId: string, data: { name: string; interests: string }) =>
      apiFetch<{ success: boolean; student: Student }>(`/students/${studentId}`, { method: 'PATCH', body: JSON.stringify(data) }),

    erase: (studentId: string) =>
      apiFetch<{ success: boolean }>(`/students/${studentId}?confirm=true`, { method: 'DELETE' }),

  },

  // Chapters
  chapters: {
    getById: (chapterId: string) =>
      apiFetch<{
        success: boolean;
        chapter: ChapterWithPanels;
      }>(`/chapters/${chapterId}`),

    delete: (chapterId: string) =>
      apiFetch<{
        success: boolean;
        message: string;
      }>(`/chapters/${chapterId}?confirm=true`, {
        method: 'DELETE',
      }),
  },

  settings: {
    get: () => apiFetch<{
      settings: {
        story_length: 12 | 20;
        default_design_style: 'manga' | 'comic' | 'cartoon';
        openai_model: 'gpt-5.1';
        bfl_model: 'flux-2-pro';
        automatic_panel_review: boolean;
        panel_review_attempt_cap: 1 | 2 | 3;
        reader_preferences: Record<string, boolean>;
      };
      provider_readiness: { openai: boolean; bfl: boolean };
      local_data: string;
    }>('/settings'),
    update: (settings: Awaited<ReturnType<typeof api.settings.get>>['settings']) =>
      apiFetch<{ success: boolean }>('/settings', { method: 'PATCH', body: JSON.stringify(settings) }),
    reset: () => apiFetch<{ success: boolean }>('/settings/reset-local-data?confirm=true', { method: 'POST' }),
  },
};

export default api;
