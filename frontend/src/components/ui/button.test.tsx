import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "./button";

describe("Button", () => {
  it("keeps icon-only small buttons at least 44 pixels wide", () => {
    render(<Button size="sm" aria-label="Change layout" />);

    expect(screen.getByRole("button", { name: "Change layout" })).toHaveClass("min-w-11");
  });
});
