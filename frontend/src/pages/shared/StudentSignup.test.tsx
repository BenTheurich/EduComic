import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StudentSignup from "./StudentSignup";

const { createStudent, createAvatar } = vi.hoisted(() => ({
  createStudent: vi.fn(),
  createAvatar: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    students: { create: createStudent },
    avatar: { create: createAvatar },
  },
}));

vi.mock("sonner", () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() },
}));

describe("StudentSignup", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    createStudent.mockReset().mockResolvedValue({ student: { id: "student-1" } });
    createAvatar.mockReset().mockResolvedValue({ student: { id: "student-1" } });
  });

  it("creates a text-only student without offering a photo upload", async () => {
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/student/signup"]}
      >
        <Routes>
          <Route path="/student/signup" element={<StudentSignup />} />
          <Route path="/student/dashboard/:studentId" element={<h1>Student dashboard</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByLabelText(/photo/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: "Ada" } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: "Lovelace" } });
    fireEvent.change(screen.getByLabelText(/interests/i), { target: { value: "robots" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => expect(createStudent).toHaveBeenCalledWith("Ada Lovelace", "robots"));
    expect(await screen.findByRole("heading", { name: "Student dashboard" })).toBeInTheDocument();
  });
});
