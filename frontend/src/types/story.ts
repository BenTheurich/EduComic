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
  revision: number;
  chapter_outline: string | null;
  original_prompt: string;
  thumbnail_url: string | null;
  story_title?: string;
  status: ChapterStatus;
  created_at: string;
  grounded_sources?: Array<{
    material_id: string;
    content_hash: string;
    source_label: string;
    excerpts: Array<{ page: number; text: string }>;
  }>;
}

export interface ChapterWithPanels extends Chapter {
  panels: Panel[];
}

export interface ChapterPreview extends Chapter {
  classroom_name: string;
  classroom_subject: string;
}
