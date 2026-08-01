import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";

afterEach(() => vi.unstubAllGlobals());

describe("active POST request bodies", () => {
  it.each([
    {
      send: () => api.classrooms.create({
        name: "Science",
        subject: "physics",
        grade_level: "8",
        story_theme: "space",
        design_style: "comic",
      }),
      path: "/classrooms",
      body: {
        name: "Science",
        subject: "physics",
        grade_level: "8",
        story_theme: "space",
        design_style: "comic",
      },
    },
    {
      send: () => api.students.create("Ada", "robots"),
      path: "/students/create",
      body: { name: "Ada", interests: "robots" },
    },
    {
      send: () => api.story.startChapter("00000000-0000-4000-8000-000000000001", "Newton's laws"),
      path: "/classrooms/00000000-0000-4000-8000-000000000001/chapters/start",
      body: { lesson_prompt: "Newton's laws" },
    },
    {
      send: () => api.story.chooseIdea(
        "00000000-0000-4000-8000-000000000002",
        "idea_1",
      ),
      path: "/chapters/00000000-0000-4000-8000-000000000002/choose-idea",
      body: { idea_id: "idea_1" },
    },
  ])("sends $path values as JSON", async ({ send, path, body }) => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await send();

    expect(fetchMock).toHaveBeenCalledWith(
      `http://127.0.0.1:8000${path}`,
      expect.objectContaining({ method: "POST", body: JSON.stringify(body) }),
    );
  });
});
