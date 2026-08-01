import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TeacherSidebar } from "@/components/teacher/TeacherSidebar";
import ClassroomDetail from "./ClassroomDetail";

const { getById, getChapters, updateClassroom, leaveClassroom, eraseStudent } = vi.hoisted(() => ({
  getById: vi.fn(),
  getChapters: vi.fn(),
  updateClassroom: vi.fn(),
  leaveClassroom: vi.fn(),
  eraseStudent: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    classrooms: { getById, getChapters, update: updateClassroom },
    students: { leaveClassroom, erase: eraseStudent },
    chapters: { getById: vi.fn(), delete: vi.fn() },
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
    updateClassroom.mockReset().mockRejectedValue(new Error("offline"));
    leaveClassroom.mockReset().mockResolvedValue({ success: true });
    eraseStudent.mockReset().mockResolvedValue({ success: true });
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

  it("keeps a failed load visible and retries the classroom", async () => {
    getById
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({
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

    render(
      <MemoryRouter future={routerOptions} initialEntries={["/teacher/classroom/classroom-1"]}>
        <Routes>
          <Route path="/teacher/classroom/:id" element={<ClassroomDetail />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to load classroom");
    expect(screen.queryByText("Classroom not found")).not.toBeInTheDocument();
    expect(screen.queryByText(/No stories yet/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("heading", { name: "Science" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("exposes the invite copy action as a named 44-pixel target", async () => {
    render(
      <MemoryRouter future={routerOptions} initialEntries={["/teacher/classroom/classroom-1"]}>
        <Routes>
          <Route path="/teacher/classroom/:id" element={<ClassroomDetail />} />
        </Routes>
      </MemoryRouter>,
    );

    const copyInvite = await screen.findByRole("button", { name: "Copy invite link" });
    expect(copyInvite).toHaveClass("h-11", "min-w-11");
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

  it("preserves classroom edit values after a recoverable save failure", async () => {
    render(
      <MemoryRouter future={routerOptions} initialEntries={["/teacher/classroom/classroom-1"]}>
        <Routes><Route path="/teacher/classroom/:id" element={<ClassroomDetail />} /></Routes>
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Science" });

    fireEvent.click(screen.getByRole("button", { name: "Edit classroom" }));
    const name = screen.getByLabelText("Classroom name");
    fireEvent.change(name, { target: { value: "Fictional Physics Lab" } });
    fireEvent.click(screen.getByRole("button", { name: "Save classroom" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("could not be saved");
    expect(name).toHaveValue("Fictional Physics Lab");
  });

  it("keeps classroom removal distinct and confirmable", async () => {
    getById.mockResolvedValueOnce({ success: true, classroom: {
      id: "classroom-1", name: "Science", subject: "Physics", grade_level: "8", story_theme: "Space", design_style: "comic",
      students: [{ id: "student-1", name: "Mina", interests: "bridges", avatar_url: null, created_at: "2026-08-01T00:00:00Z" }],
    }});
    render(<MemoryRouter future={routerOptions} initialEntries={["/teacher/classroom/classroom-1?tab=students"]}><Routes><Route path="/teacher/classroom/:id" element={<ClassroomDetail />} /></Routes></MemoryRouter>);
    await screen.findByText("Mina");

    fireEvent.click(screen.getByRole("button", { name: "Remove Mina from classroom" }));
    expect(leaveClassroom).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm classroom removal" }));
    await waitFor(() => expect(leaveClassroom).toHaveBeenCalledWith("student-1", "classroom-1"));
    expect(eraseStudent).not.toHaveBeenCalled();
  });
});
