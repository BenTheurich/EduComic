import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Landing from "./Landing";

describe("Landing", () => {
  it("leads with the comic and role entry points without setup copy", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Turn a lesson into a comic starring your class." })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Fictional student investigates rainfall outside the Weather Lab" })).toBeInTheDocument();
    expect(screen.getByText("Fictional classroom sample")).toBeInTheDocument();
    expect(screen.queryByText(/BYOK|local project data|bring your own API keys/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get Started as Teacher" })).toHaveAttribute("href", "/teacher/dashboard");
    expect(screen.getByRole("link", { name: "Choose Student Profile" })).toHaveAttribute("href", "/student/select");
  });
});
