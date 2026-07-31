import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StudentDashboard from "./StudentDashboard";

const { getChapters, getStudent } = vi.hoisted(() => ({
  getChapters: vi.fn(),
  getStudent: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    students: {
      getById: getStudent,
      getChapters,
    },
  },
}));

describe("StudentDashboard", () => {
  beforeEach(() => {
    getStudent.mockReset().mockResolvedValue({
      success: true,
      student: {
        id: "student-1",
        name: "Ada Student",
        interests: "Space",
        photo_url: null,
        avatar_url: null,
        created_at: "2026-07-01T00:00:00Z",
      },
      classrooms: [],
    });
    getChapters.mockReset().mockResolvedValue({
      success: true,
      chapters: [
        {
          id: "generating",
          status: "generating",
          story_title: "Still Generating",
          created_at: "2026-07-31T03:00:00Z",
        },
        {
          id: "failed",
          status: "failed",
          story_title: "Failed Story",
          created_at: "2026-07-31T02:00:00Z",
        },
        {
          id: "ready",
          status: "ready",
          story_title: "Ready Story",
          index: 1,
          chapter_outline: "A complete story",
          original_prompt: "Lesson",
          thumbnail_url: null,
          classroom_name: "Science",
          created_at: "2026-07-31T01:00:00Z",
        },
      ],
    });
  });

  it("shows and links the newest ready chapter instead of newer unreadable chapters", async () => {
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/student/dashboard/student-1"]}
      >
        <Routes>
          <Route path="/student/dashboard/:studentId" element={<StudentDashboard />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Ready Story")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Read Now" })).toHaveAttribute("href", "/student/story/ready/student-1");
    expect(screen.queryByText("Still Generating")).not.toBeInTheDocument();
    expect(screen.queryByText("Failed Story")).not.toBeInTheDocument();
  });
});
