import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TeacherSidebar } from "@/components/teacher/TeacherSidebar";
import ClassroomDetail from "./ClassroomDetail";

const { getById, getChapters } = vi.hoisted(() => ({
  getById: vi.fn(),
  getChapters: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    classrooms: { getById, getChapters },
  },
}));

const routerOptions = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

describe("removed classroom materials feature", () => {
  beforeEach(() => {
    getById.mockReset().mockResolvedValue({
      success: true,
      classroom: {
        id: "classroom-1",
        name: "Science",
        subject: "Physics",
        grade_level: "8",
        story_theme: "Space",
        design_style: "comic",
        created_at: "2026-07-31T00:00:00Z",
        students: [],
      },
    });
    getChapters.mockReset().mockResolvedValue({ success: true, chapters: [] });
  });

  it("does not offer a Materials tab in the real classroom detail", async () => {
    render(
      <MemoryRouter future={routerOptions} initialEntries={["/teacher/classroom/classroom-1"]}>
        <Routes>
          <Route path="/teacher/classroom/:id" element={<ClassroomDetail />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Science" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Materials" })).not.toBeInTheDocument();
  });

  it("does not offer a Materials link in the real teacher sidebar", () => {
    render(
      <MemoryRouter future={routerOptions} initialEntries={["/teacher/classroom/classroom-1"]}>
        <Routes>
          <Route
            path="/teacher/classroom/:id"
            element={<TeacherSidebar open setOpen={() => undefined} />}
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getAllByRole("link", { name: "Students" })).toHaveLength(2);
    expect(screen.queryAllByRole("link", { name: "Materials" })).toHaveLength(0);
  });
});
