export interface Panel {
  id: string;
  chapter_id: string;
  index: number;
  image: string;
  created_at: string;
}

export type ChapterStatus =
  | 'draft'
  | 'awaiting_choice'
  | 'options_generated'
  | 'idea_chosen'
  | 'generating'
  | 'ready'
  | 'failed';

export interface Chapter {
  id: string;
  classroom_id: string;
  index: number;
  chapter_outline: string | null;
  original_prompt: string;
  thumbnail_url: string | null;
  story_title?: string;
  status: ChapterStatus;
  created_at: string;
}

export interface ChapterWithPanels extends Chapter {
  panels: Panel[];
}

export interface ChapterPreview extends Chapter {
  classroom_name: string;
  classroom_subject: string;
}

// Legacy Story types (kept for backwards compatibility with teacher components)
export interface Story {
  id: string;
  classroom_id: string;
  lesson_prompt: string;
  title: string;
  status: 'generating' | 'completed' | 'failed' | 'regenerating';
  progress: number;
  created_at: string;
  design_style?: 'manga' | 'comic' | 'cartoon';
}

export interface StoryWithPanels extends Story {
  panels: Panel[];
}

export interface StoryPreview {
  id: string;
  title: string;
  created_at: string;
  thumbnail_url: string;
  classroom_name: string;
}
