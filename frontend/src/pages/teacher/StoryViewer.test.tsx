import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StoryViewer from "./StoryViewer";

const { getChapter, getChapters } = vi.hoisted(() => ({
  getChapter: vi.fn(),
  getChapters: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    chapters: { getById: getChapter },
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
    vi.stubGlobal("ResizeObserver", class {
      observe() {}
      unobserve() {}
      disconnect() {}
    });
  });

  afterEach(() => vi.unstubAllGlobals());

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
});
