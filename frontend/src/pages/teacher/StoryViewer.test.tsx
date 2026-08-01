import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StoryViewer from "./StoryViewer";

const { getChapter, getChapters, regeneratePanel, getPanelRegeneration } = vi.hoisted(() => ({
  getChapter: vi.fn(),
  getChapters: vi.fn(),
  regeneratePanel: vi.fn(),
  getPanelRegeneration: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    chapters: { getById: getChapter, regeneratePanel, getPanelRegeneration },
    classrooms: { getChapters },
  },
}));

const LocationProbe = () => <output aria-label="Current path">{useLocation().pathname}</output>;

const renderViewer = () => render(
  <MemoryRouter
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    initialEntries={["/teacher/story/current"]}
  >
    <LocationProbe />
    <Routes>
      <Route path="/teacher/story/:id" element={<StoryViewer />} />
    </Routes>
  </MemoryRouter>,
);

describe("StoryViewer", () => {
  beforeEach(() => {
    getChapter.mockReset();
    getChapters.mockReset();
    regeneratePanel.mockReset();
    getPanelRegeneration.mockReset();
    localStorage.clear();
    vi.stubGlobal("ResizeObserver", class {
      observe() {}
      unobserve() {}
      disconnect() {}
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("exposes reader controls and clamps a malformed saved scale", async () => {
    localStorage.setItem("teacherStoryReaderImageScale", "not-a-number");
    getChapter.mockResolvedValue({
      success: true,
      chapter: {
        id: "current", classroom_id: "classroom-1", index: 1, chapter_outline: null,
        original_prompt: "Lesson", thumbnail_url: null, story_title: "Gravity", status: "ready",
        created_at: "2026-01-01", panels: [],
      },
    });
    getChapters.mockResolvedValue({ success: true, chapters: [] });

    renderViewer();

    const slider = await screen.findByRole("slider", { name: "Image size" });
    expect(slider).toHaveAttribute("aria-valuenow", "50");
    expect(slider).toHaveAttribute("aria-valuetext", "50 percent");
    expect(screen.getByRole("button", { name: "Vertical layout" })).toHaveAttribute("aria-pressed", "true");
    const grid = screen.getByRole("button", { name: "Grid layout" });
    fireEvent.click(grid);
    expect(grid).toHaveAttribute("aria-pressed", "true");
  });

  it("fails closed when a chapter is not ready", async () => {
    getChapter.mockResolvedValueOnce({
      success: true,
      chapter: {
        id: "current",
        classroom_id: "classroom-1",
        index: 1,
        story_title: "Unfinished Story",
        status: "generating",
        panels: [],
      },
    }).mockImplementation(() => new Promise(() => {}));

    renderViewer();

    expect(await screen.findByRole("alert")).toHaveTextContent("generating");
    expect(screen.queryByText("Unfinished Story")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Export PDF" })).not.toBeInTheDocument();
    expect(getChapters).not.toHaveBeenCalled();
  });

  it("navigates only between ready chapters", async () => {
    getChapter.mockResolvedValueOnce({
      success: true,
      chapter: {
        id: "current",
        classroom_id: "classroom-1",
        index: 2,
        story_title: "Current Story",
        status: "ready",
        panels: [],
      },
    }).mockImplementation(() => new Promise(() => {}));
    getChapters.mockResolvedValue({
      success: true,
      chapters: [
        { id: "generating", status: "generating", created_at: "2026-07-31T04:00:00Z" },
        { id: "current", status: "ready", created_at: "2026-07-31T03:00:00Z" },
        { id: "failed", status: "failed", created_at: "2026-07-31T02:00:00Z" },
        { id: "older-ready", status: "ready", created_at: "2026-07-31T01:00:00Z" },
      ],
    });

    renderViewer();

    fireEvent.click(await screen.findByRole("button", { name: "Previous Story" }));
    await waitFor(() => expect(screen.getByLabelText("Current path")).toHaveTextContent("/teacher/story/older-ready"));
  });

  it("keeps the old panel visible during a correction failure and permits retry", async () => {
    getChapter.mockResolvedValue({
      success: true,
      chapter: {
        id: "current", classroom_id: "classroom-1", index: 1, revision: 1,
        original_prompt: "Lesson", thumbnail_url: null, story_title: "Gravity", status: "ready",
        created_at: "2026-01-01",
        panels: [{ id: "panel-2", chapter_id: "current", index: 2, image: "/media/old.png", created_at: "2026-01-01" }],
      },
    });
    getChapters.mockResolvedValue({ success: true, chapters: [] });
    regeneratePanel.mockRejectedValue(new Error("fictional provider failure"));

    renderViewer();
    fireEvent.click(await screen.findByRole("button", { name: "Correct panel 2" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Correction for panel 2" }), {
      target: { value: "Make the arrow clockwise." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Regenerate panel 2" }));

    expect(screen.getByRole("img", { name: "Panel 2" })).toHaveAttribute("src", "/media/old.png");
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be regenerated");
    expect(screen.getByRole("button", { name: "Retry panel 2" })).toBeEnabled();
    expect(screen.getByRole("textbox", { name: "Correction for panel 2" })).toHaveValue("Make the arrow clockwise.");
  });

  it("shows progress over the old panel then reloads the published replacement", async () => {
    const chapter = {
      id: "current", classroom_id: "classroom-1", index: 1, revision: 1,
      original_prompt: "Lesson", thumbnail_url: null, story_title: "Gravity", status: "ready",
      created_at: "2026-01-01",
      panels: [{ id: "panel-2", chapter_id: "current", index: 2, image: "/media/old.png", created_at: "2026-01-01" }],
    };
    getChapter
      .mockResolvedValueOnce({ success: true, chapter })
      .mockResolvedValueOnce({
        success: true,
        chapter: {
          ...chapter,
          revision: 2,
          panels: [{ ...chapter.panels[0], image: "/media/replacement.png" }],
        },
      });
    getChapters.mockResolvedValue({ success: true, chapters: [] });
    regeneratePanel.mockResolvedValue({ run_id: "run-1", status: "regenerating" });
    getPanelRegeneration.mockResolvedValue({ run_id: "run-1", status: "ready" });

    renderViewer();
    fireEvent.click(await screen.findByRole("button", { name: "Correct panel 2" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Correction for panel 2" }), {
      target: { value: "Make the arrow clockwise." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Regenerate panel 2" }));

    expect(await screen.findByText("Regenerating panel 2...")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Panel 2" })).toHaveAttribute("src", "/media/old.png");
    await waitFor(
      () => expect(screen.getByRole("img", { name: "Panel 2" })).toHaveAttribute("src", "/media/replacement.png"),
      { timeout: 2000 },
    );
    expect(getPanelRegeneration).toHaveBeenCalledWith("run-1");
  });
});
