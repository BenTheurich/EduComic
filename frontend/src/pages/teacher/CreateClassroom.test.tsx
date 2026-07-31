import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import CreateClassroom from "./CreateClassroom";

vi.mock("@/lib/api", () => ({ api: { classrooms: { create: vi.fn() } } }));

describe("CreateClassroom", () => {
  it("selects the design style through a labelled radio group", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <CreateClassroom />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Classroom Name *"), { target: { value: "Physics" } });
    fireEvent.click(screen.getByRole("combobox", { name: "Subject *" }));
    fireEvent.click(screen.getByRole("option", { name: "physics" }));
    fireEvent.click(screen.getByRole("combobox", { name: "Grade Level *" }));
    fireEvent.click(screen.getByRole("option", { name: "Grade 8" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    const manga = screen.getByRole("radio", { name: "Manga" });
    expect(manga).not.toBeChecked();
    fireEvent.click(manga);
    expect(manga).toBeChecked();
    expect(screen.getByRole("radiogroup", { name: "Design Style *" })).toBeInTheDocument();
  });
});
