/**
 * API client configuration and utilities
 */
import type { Chapter, ChapterPreview, ChapterStatus, ChapterWithPanels } from "@/types/story";
import type { Student } from "@/types/student";

const API_BASE_URL = import.meta.env.VITE_API_URL || (
  import.meta.env.DEV || import.meta.env.MODE === 'test'
    ? 'http://localhost:8000'
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
  health: () => apiFetch<{ status: string; supabase_configured: boolean }>('/health'),

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
            photo_url: string | null;
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
          photo_url: string | null;
          created_at: string;
        }>;
      }>(`/classrooms/${classroomId}/students`),

    getChapters: (classroomId: string) =>
      apiFetch<{
        success: boolean;
        chapters: Chapter[];
      }>(`/classrooms/${classroomId}/chapters`),

    getMaterials: (classroomId: string) =>
      apiFetch<{
        success: boolean;
        materials: Array<{
          id: string;
          classroom_id: string;
          title: string;
          description: string | null;
          file_url: string;
          file_type: string;
          week_number: number | null;
          created_at: string;
        }>;
      }>(`/classrooms/${classroomId}/materials`),

    uploadMaterial: async (
      classroomId: string,
      file: File,
      title: string,
      description?: string,
      weekNumber?: number
    ) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title);
      if (description) formData.append('description', description);
      if (weekNumber) formData.append('week_number', weekNumber.toString());

      const response = await fetch(
        `${API_BASE_URL}/classrooms/${classroomId}/materials/upload`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Failed to upload material');
      }

      return await response.json() as {
        success: boolean;
        material: {
          id: string;
          classroom_id: string;
          title: string;
          description: string | null;
          file_url: string;
          file_type: string;
          week_number: number | null;
          created_at: string;
        };
      };
    },

    deleteMaterial: (materialId: string) =>
      apiFetch<{
        success: boolean;
        message: string;
      }>(`/materials/${materialId}`, {
        method: 'DELETE',
      }),
  },

  // Story generation
  story: {
    generateOptions: (classroomId: string, lessonPrompt: string) =>
      apiFetch<{
        success: boolean;
        options: Array<{
          id: string;
          title: string;
          summary: string;
          theme: string;
        }>;
      }>(`/story/generate-options?classroom_id=${classroomId}&lesson_prompt=${encodeURIComponent(lessonPrompt)}`, {
        method: 'POST',
      }),

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

    chooseIdea: (chapterId: string, ideaId: string, thumbnailUrl?: string) =>
      apiFetch<{
        success: boolean;
        chapter: Chapter;
      }>(`/chapters/${chapterId}/choose-idea`, {
        method: 'POST',
        body: JSON.stringify({ idea_id: ideaId, thumbnail_url: thumbnailUrl ?? null }),
      }),

    commitChapter: (chapterId: string, ideaId: string) =>
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
          photo_url: string | null;
          avatar_url: string | null;
          created_at: string;
        }>;
      }>('/students'),

    create: (name: string, interests: string, photoUrl?: string) =>
      apiFetch<{
        success: boolean;
        student: {
          id: string;
          name: string;
          interests: string;
          photo_url: string | null;
          avatar_url: string | null;
          created_at: string;
        };
      }>('/students/create', {
        method: 'POST',
        body: JSON.stringify({ name, interests, photo_url: photoUrl ?? null }),
      }),

    joinClassroom: (studentId: string, classroomId: string) =>
      apiFetch<{
        success: boolean;
        message: string;
        student: {
          id: string;
          name: string;
          interests: string;
          photo_url: string | null;
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
          photo_url: string | null;
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
      }>(`/students/${studentId}/leave-classroom/${classroomId}`, {
        method: 'DELETE',
      }),

    uploadPhoto: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('filename', file.name);

      return apiFetch<{ success: boolean; photo_url: string }>('/students/upload-photo', {
        method: 'POST',
        body: formData,
      });
    },
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
      }>(`/chapters/${chapterId}`, {
        method: 'DELETE',
      }),
  },
};

export default api;
