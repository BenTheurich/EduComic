import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StoryGenerator from "./StoryGenerator";

const { chooseIdea, commitChapter, getChapter, getClassroom, startChapter } = vi.hoisted(() => ({
  chooseIdea: vi.fn(),
  commitChapter: vi.fn(),
  getChapter: vi.fn(),
  getClassroom: vi.fn(),
  startChapter: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    classrooms: {
      getById: getClassroom,
    },
    story: {
      startChapter,
      chooseIdea,
      commitChapter,
    },
    chapters: { getById: getChapter },
  },
}));

const chapterResponse = (status: string, panels: unknown[] = []) => ({
  success: true,
  chapter: { id: "chapter-1", status, panels },
});

const renderGenerator = () => render(
  <MemoryRouter
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    initialEntries={["/teacher/classroom/classroom-1/story/new"]}
  >
    <Routes>
      <Route path="/teacher/classroom/:classroomId/story/new" element={<StoryGenerator />} />
    </Routes>
  </MemoryRouter>,
);

const startGeneration = async (fakeTimers = false) => {
  startChapter.mockResolvedValue({
    success: true,
    chapter: {
      id: "chapter-1",
      story_ideas: [{ id: "idea_1", title: "Orbit", summary: "A lesson", theme: "Space" }],
    },
  });
  commitChapter.mockResolvedValue({ success: true });

  renderGenerator();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Newton's laws" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate Story Options" }));
  const selectButton = await screen.findByRole("button", { name: "Select This Story" });
  if (fakeTimers) vi.useFakeTimers();
  fireEvent.click(selectButton);
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

describe("StoryGenerator", () => {
  beforeEach(() => {
    startChapter.mockReset();
    chooseIdea.mockReset().mockResolvedValue({ success: true });
    commitChapter.mockReset();
    getChapter.mockReset();
    getClassroom.mockReset().mockResolvedValue({
      success: true,
      classroom: { name: "Science", subject: "Physics", grade_level: "8" },
    });
    vi.stubGlobal("fetch", vi.fn());
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows a retryable error instead of mock choices when option generation fails", async () => {
    startChapter.mockRejectedValue(new Error("Service unavailable"));

    renderGenerator();

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Newton's laws" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate Story Options" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(screen.queryByText("Newton's Space Race")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Select This Story" })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Generate Story Options" })).toBeEnabled());
  });

  it("renders and selects story options without a thumbnail request", async () => {
    startChapter.mockResolvedValue({
      success: true,
      chapter: {
        id: "chapter-1",
        story_ideas: [{ id: "idea_1", title: "Orbit", summary: "A lesson", theme: "Space" }],
      },
    });
    commitChapter.mockResolvedValue({ success: true });
    getChapter.mockResolvedValue(chapterResponse("failed"));

    renderGenerator();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Newton's laws" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate Story Options" }));

    expect(await screen.findByText("Orbit")).toBeInTheDocument();
    expect(screen.getByText("Space")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Select This Story" }));

    await waitFor(() => expect(chooseIdea).toHaveBeenCalledWith("chapter-1", "idea_1"));
    expect(fetch).not.toHaveBeenCalled();
  });

  it("resets the consecutive polling failure limit after a successful poll", async () => {
    getChapter.mockRejectedValueOnce(new Error("offline"));
    getChapter.mockResolvedValueOnce(chapterResponse("generating"));
    for (let attempt = 0; attempt < 10; attempt += 1) {
      getChapter.mockRejectedValueOnce(new Error("offline"));
    }

    await startGeneration(true);

    await act(async () => vi.advanceTimersByTimeAsync(20_000));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await act(async () => vi.advanceTimersByTimeAsync(2_000));
    expect(screen.getByRole("alert")).toHaveTextContent("Lost connection");
  });

  it("stops polling and offers a retry when generation fails", async () => {
    getChapter.mockResolvedValue(chapterResponse("failed"));

    await startGeneration(true);

    expect(screen.getByRole("alert")).toHaveTextContent("Story generation failed");
    expect(screen.getByRole("button", { name: "Try another story" })).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(4_000));
    expect(getChapter).toHaveBeenCalledTimes(1);
  });

  it("shows panel progress without inventing an expected panel count", async () => {
    getChapter.mockResolvedValue(chapterResponse("generating", [{
      id: "panel-1",
      chapter_id: "chapter-1",
      index: 1,
      image: "panel.png",
      created_at: "2026-07-31T00:00:00Z",
    }]));

    await startGeneration();

    expect(screen.getByText("1 panel completed")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveClass("animate-pulse");
    expect(screen.queryByText(/\/ 12/)).not.toBeInTheDocument();
  });
});
