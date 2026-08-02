import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Landing from "./Landing";

describe("Landing", () => {
  it("links teachers and students to their entry routes", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /Turn today’s lesson into a comic/i })).toBeInTheDocument();
    expect(screen.getByText(/Local project data · bring your own API keys/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get Started as Teacher" })).toHaveAttribute("href", "/teacher/dashboard");
    expect(screen.getByRole("link", { name: "Choose Student Profile" })).toHaveAttribute("href", "/student/select");
  });
});
