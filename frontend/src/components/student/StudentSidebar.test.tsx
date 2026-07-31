import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StudentSidebar } from "./StudentSidebar";

const { getClassrooms } = vi.hoisted(() => ({ getClassrooms: vi.fn() }));

vi.mock("@/lib/api", () => ({
  default: { students: { getClassrooms } },
}));

describe("StudentSidebar", () => {
  beforeEach(() => {
    vi.stubGlobal("scrollTo", vi.fn());
    getClassrooms.mockReset().mockImplementation(() => new Promise(() => undefined));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

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

  it("shows and retries a failed classroom list", async () => {
    getClassrooms
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ classrooms: [{ id: "classroom-1", name: "Physics Lab" }] });

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <StudentSidebar studentId="student-1" open setOpen={() => undefined} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "My Classrooms" })[0]);
    expect((await screen.findAllByRole("alert"))[0]).toHaveTextContent("Failed to load classrooms");
    fireEvent.click(screen.getAllByRole("button", { name: "Retry classrooms" })[0]);

    expect((await screen.findAllByRole("link", { name: "Physics Lab" }))[0]).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
