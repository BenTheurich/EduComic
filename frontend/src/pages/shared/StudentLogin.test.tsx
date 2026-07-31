import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StudentLogin from "./StudentLogin";

const { getAllStudents } = vi.hoisted(() => ({ getAllStudents: vi.fn() }));

vi.mock("@/lib/api", () => ({
  api: { students: { getAll: getAllStudents } },
}));

const LocationProbe = () => <output aria-label="Current path">{useLocation().pathname}</output>;

const renderLogin = () => render(
  <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/student/login"]}>
    <LocationProbe />
    <Routes><Route path="*" element={<StudentLogin />} /></Routes>
  </MemoryRouter>,
);

describe("StudentLogin", () => {
  beforeEach(() => {
    getAllStudents.mockReset();
    localStorage.clear();
  });

  it("keeps a failed load visible and retries it", async () => {
    getAllStudents
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ students: [] });

    renderLogin();

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to load students");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(getAllStudents).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("No students found")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("uses a focusable named button for each student account", async () => {
    getAllStudents.mockResolvedValue({
      students: [{ id: "student-1", name: "Ada", interests: "Robotics", avatar_url: null, created_at: "2026-01-01" }],
    });

    renderLogin();

    const account = await screen.findByRole("button", { name: /Continue as Ada/ });
    expect(account.tagName).toBe("BUTTON");
    account.focus();
    expect(account).toHaveFocus();
    fireEvent.click(account);

    expect(localStorage.getItem("studentId")).toBe("student-1");
    expect(screen.getByLabelText("Current path")).toHaveTextContent("/student/dashboard/student-1");
  });
});
