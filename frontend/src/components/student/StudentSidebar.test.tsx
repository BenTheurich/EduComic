import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { StudentSidebar } from "./StudentSidebar";

vi.mock("@/lib/api", () => ({
  default: { students: { getClassrooms: vi.fn(() => new Promise(() => undefined)) } },
}));

describe("StudentSidebar", () => {
  it("names collapsed links and exposes classroom disclosure state", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <StudentSidebar studentId="student-1" open={false} setOpen={() => undefined} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    const disclosure = screen.getAllByRole("button", { name: "My Classrooms" })[0];
    expect(disclosure).toHaveAttribute("aria-expanded", "false");
    expect(disclosure).not.toHaveAttribute("aria-controls");
    fireEvent.click(disclosure);
    expect(disclosure).toHaveAttribute("aria-expanded", "true");
  });
});
