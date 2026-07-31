import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { StudentLayout } from "./student/StudentLayout";
import { TeacherLayout } from "./teacher/TeacherLayout";

describe("responsive app layouts", () => {
  it.each([
    ["teacher", TeacherLayout, "Teacher content"],
    ["student", StudentLayout, "Student content"],
  ])("stacks the %s sidebar above content on mobile and beside it on desktop", (_name, Layout, content) => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Layout>{content}</Layout>
      </MemoryRouter>,
    );

    expect(screen.getByText(content).parentElement).toHaveClass("flex-col", "md:flex-row");
  });
});
