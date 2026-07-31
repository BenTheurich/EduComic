import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StoryGenerator from "./StoryGenerator";

const { startChapter } = vi.hoisted(() => ({ startChapter: vi.fn() }));

vi.mock("@/lib/api", () => ({
  api: {
    classrooms: {
      getById: vi.fn().mockResolvedValue({
        success: true,
        classroom: { name: "Science", subject: "Physics", grade_level: "8" },
      }),
    },
    story: {
      startChapter,
      chooseIdea: vi.fn(),
      commitChapter: vi.fn(),
    },
    chapters: { getById: vi.fn() },
  },
}));

vi.mock("@/services/thumbnailGenerator", () => ({
  generateStoryThumbnails: vi.fn(),
}));

describe("StoryGenerator", () => {
  beforeEach(() => {
    startChapter.mockReset();
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => vi.restoreAllMocks());

  it("shows a retryable error instead of mock choices when option generation fails", async () => {
    startChapter.mockRejectedValue(new Error("Service unavailable"));

    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/teacher/classroom/classroom-1/story/new"]}
      >
        <Routes>
          <Route path="/teacher/classroom/:classroomId/story/new" element={<StoryGenerator />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Newton's laws" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate Story Options" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(screen.queryByText("Newton's Space Race")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Select This Story" })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Generate Story Options" })).toBeEnabled());
  });
});
