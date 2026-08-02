import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Landing from "./Landing";

describe("Landing", () => {
  it("shows the fictional portrait-to-avatar-to-comic transformation", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Turn a lesson into a comic starring your class." })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Fictional portrait of Maya Rivers" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Comic avatar generated from Maya's fictional portrait" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Maya and her fictional classmates investigate condensation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "From lesson material to finished story." })).toBeInTheDocument();
  });

  it("offers only working role and workflow links without setup copy", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/BYOK|local project data|bring your own API keys/i)).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Teacher workspace" })[0]).toHaveAttribute("href", "/teacher/dashboard");
    expect(screen.getAllByRole("link", { name: "Student profiles" })[0]).toHaveAttribute("href", "/student/select");
    expect(screen.getByRole("link", { name: /see how it works/i })).toHaveAttribute("href", "#how-it-works");
  });
});
