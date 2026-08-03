import type { ChapterPreview, ChapterWithPanels } from "@/types/story";
import type { Student } from "@/types/student";
import { assetUrl } from "@/lib/runtime";

export const DEMO_CLASSROOM_ID = "class-5b-science";
export const DEMO_CHAPTER_ID = "misty-jar";
const createdAt = "2026-08-02T10:00:00Z";

const studentDetails = [
  ["maya-rivers", "Maya Rivers", "Weather mysteries, drawing, and soccer"],
  ["leo-martinez", "Leo Martinez", "Robotics, basketball, and science experiments"],
  ["amara-johnson", "Amara Johnson", "Dance, animals, and nature journals"],
  ["noah-chen", "Noah Chen", "Space, puzzles, and coding"],
  ["sophie-miller", "Sophie Miller", "Clouds, painting, and gymnastics"],
  ["eli-williams", "Eli Williams", "Building, football, and inventions"],
  ["priya-shah", "Priya Shah", "Books, chemistry, and music"],
  ["finn-murphy", "Finn Murphy", "Sketching, hiking, and weather"],
] as const;

export const demoStudents: Student[] = studentDetails.map(([id, name, interests], index) => {
  const avatar = assetUrl(`demo/how-it-works/avatar-${String(index + 1).padStart(2, "0")}.png`);
  return {
    id,
    name,
    interests,
    avatar_url: avatar,
    avatar_thumbnail_url: avatar,
    created_at: createdAt,
  };
});

export const demoClassroom = {
  id: DEMO_CLASSROOM_ID,
  name: "Class 5B Science",
  subject: "Science",
  grade_level: "Grade 5",
  story_theme: "Weather mysteries",
  design_style: "comic",
  student_count: 8,
  story_count: 1,
  created_at: createdAt,
};

export const demoMaterial = {
  id: "clouds-and-rain-material",
  classroom_id: DEMO_CLASSROOM_ID,
  source_filename: "How clouds make rain.pdf",
  extraction_state: "ready" as const,
  content_hash: "fictional-demo-clouds-and-rain",
  page_count: 3,
  text_char_count: 1842,
};

export const demoChapter: ChapterWithPanels = {
  id: DEMO_CHAPTER_ID,
  classroom_id: DEMO_CLASSROOM_ID,
  index: 1,
  revision: 1,
  chapter_outline: "Eight classmates solve the mystery of condensation on a cold jar.",
  original_prompt: "Teach how cooling water vapor forms droplets, clouds, and rain.",
  thumbnail_url: assetUrl("demo/stories/misty-jar/panels/panel-01.png"),
  story_title: "The Mystery of the Misty Jar",
  story_description: "Eight classmates connect condensation on a cold jar to clouds and rain.",
  status: "ready",
  created_at: createdAt,
  grounded_sources: [{
    material_id: demoMaterial.id,
    content_hash: demoMaterial.content_hash,
    source_label: demoMaterial.source_filename,
    excerpts: [{ page: 1, text: "Water vapor cools and condenses into liquid droplets." }],
  }],
  panels: Array.from({ length: 12 }, (_, offset) => {
    const index = offset + 1;
    return {
      id: `misty-jar-panel-${index}`,
      chapter_id: DEMO_CHAPTER_ID,
      index,
      image: assetUrl(`demo/stories/misty-jar/panels/panel-${String(index).padStart(2, "0")}.png`),
      created_at: createdAt,
    };
  }),
};

export const demoChapterPreview: ChapterPreview = {
  ...demoChapter,
  classroom_name: demoClassroom.name,
  classroom_subject: demoClassroom.subject,
};
