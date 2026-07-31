import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Sidebar, SidebarBody, SidebarLink } from "./animated-sidebar";

const SidebarFixture = () => {
  const [open, setOpen] = useState(false);

  return (
    <Sidebar open={open} setOpen={setOpen}>
      <SidebarBody>
        <nav aria-label="Primary navigation">
          <SidebarLink link={{ label: "Dashboard", href: "/dashboard", icon: <span aria-hidden="true">D</span> }} />
        </nav>
      </SidebarBody>
    </Sidebar>
  );
};

describe("animated sidebar", () => {
  it("renders navigation in both desktop and keyboard-operable mobile sidebars", async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <SidebarFixture />
      </MemoryRouter>,
    );

    const menuButton = screen.getByRole("button", { name: "Open navigation" });
    menuButton.focus();
    fireEvent.click(menuButton);

    expect(screen.getAllByRole("link", { name: "Dashboard" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Close navigation" })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => expect(screen.queryByRole("button", { name: "Close navigation" })).not.toBeInTheDocument());
    expect(menuButton).toHaveFocus();
  });
});
