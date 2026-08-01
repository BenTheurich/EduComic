import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import StudentProfile from "./StudentProfile";

const { getById, update, erase, createAvatar } = vi.hoisted(() => ({
  getById: vi.fn(), update: vi.fn(), erase: vi.fn(), createAvatar: vi.fn(),
}));
vi.mock("@/lib/api", () => ({
  default: { students: { getById, update, erase }, avatar: { create: createAvatar } },
}));

beforeEach(() => {
  getById.mockResolvedValue({ student: { id: "student-1", name: "Mina", interests: "bridges", avatar_url: "/media/avatars/old.png", created_at: "2026-08-01T00:00:00Z" } });
  update.mockReset().mockResolvedValue({ student: { id: "student-1", name: "Mina", interests: "bridges", avatar_url: "/media/avatars/old.png", created_at: "2026-08-01T00:00:00Z" } });
  createAvatar.mockReset().mockRejectedValue(new Error("provider unavailable"));
  erase.mockReset().mockResolvedValue({ success: true });
});

it("offers existing-avatar regeneration and keeps the old avatar visible on failure", async () => {
  render(<MemoryRouter initialEntries={["/student/profile/student-1"]}><Routes><Route path="/student/profile/:studentId" element={<StudentProfile />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Your current avatar stays visible until a replacement succeeds.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Regenerate avatar" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("failed");
  expect(screen.getByText("Your current avatar stays visible until a replacement succeeds.")).toBeInTheDocument();
});

it("requires confirmation before full profile erasure", async () => {
  render(<MemoryRouter initialEntries={["/student/profile/student-1"]}><Routes><Route path="/student/profile/:studentId" element={<StudentProfile />} /></Routes></MemoryRouter>);
  await screen.findByText("Mina");
  fireEvent.click(screen.getByRole("button", { name: "Erase profile and personal data" }));
  expect(erase).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm full erasure" }));
  await waitFor(() => expect(erase).toHaveBeenCalledWith("student-1"));
});
