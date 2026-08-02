import { act, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
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
    expect(screen.getByRole("heading", { name: "Your lesson. Their characters. One shared story." })).toBeInTheDocument();
  });

  it("shows the complete four-part lesson-to-comic process", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Upload your lesson." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bring in the whole class." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Turn learning into a story." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Let students see themselves learning." })).toBeInTheDocument();
  });

  it("keeps the process headline above the scrolling beats without the old lead copy", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    const heading = screen.getByRole("heading", { name: "Your lesson. Their characters. One shared story." });
    expect(heading.closest("article")).toBeNull();
    expect(screen.queryByText("Teaching materials ground the plot. Every student avatar joins the cast.")).not.toBeInTheDocument();
  });

  it("keeps each scrolling beat focused on its primary explanation", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    [
      "The teacher’s material stays at the center.",
      "Not one mascot—a recognizable classroom community.",
      "A complete printable story, grounded in the lesson.",
      "Recognition turns the finished comic into a shared class moment.",
    ].forEach((copy) => expect(screen.queryByText(copy)).not.toBeInTheDocument());
  });

  it("presents the complete printable comic without a review badge", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    expect(screen.queryAllByText("Class story · ready to review")).toHaveLength(0);
    expect(document.querySelectorAll(".landing-comic-scene.is-enlarged")).toHaveLength(2);
  });

  it("shows the lesson stack as three distinct teaching documents", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    expect(screen.getAllByText("Cloud vocabulary").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Water cycle diagram").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "How clouds make rain" })).toBeInTheDocument();
  });

  it("updates the sticky illustration when a process step reaches focus", () => {
    let notify: IntersectionObserverCallback = () => undefined;
    class TestIntersectionObserver {
      constructor(callback: IntersectionObserverCallback) {
        notify = callback;
      }

      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() { return []; }
      readonly root = null;
      readonly rootMargin = "0px";
      readonly thresholds = [];
    }
    vi.stubGlobal("IntersectionObserver", TestIntersectionObserver);

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    const castStep = screen.getByRole("heading", { name: "Bring in the whole class." }).closest("article");
    expect(castStep).not.toBeNull();

    act(() => {
      notify(
        [{ isIntersecting: true, intersectionRatio: 0.8, target: castStep } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });

    const castVisual = screen.getByRole("img", { name: "Eight student avatars joining the comic cast" });
    expect(castVisual).toHaveClass("landing-process-visual-cast");
    expect(castVisual.querySelector(".landing-mini-materials")).toBeNull();
    expect(castVisual.querySelector(".landing-flow-arrow")).toBeNull();
    expect(castVisual.querySelectorAll(".landing-avatar")).toHaveLength(8);
    expect(castVisual.querySelector(".landing-cast-scene")).toHaveClass("is-balanced");
    vi.unstubAllGlobals();
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

  it("credits the five creators and the tools used to build EduComic", () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Landing />
      </MemoryRouter>,
    );

    const team = screen.getByRole("region", { name: "Meet the team behind EduComic." });
    const names = within(team).getAllByTestId("team-member-name").map((node) => node.textContent);
    expect(names).toEqual([
      "Florian Schwieren",
      "Pouya Shekarchizadeh",
      "Anastasia Koslova",
      "Tim Gaydoul",
      "Ben Theurich",
    ]);

    expect(within(team).getByRole("link", { name: "Florian Schwieren on LinkedIn" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/florian-schwieren-618750215/",
    );
    expect(within(team).getByRole("link", { name: "Pouya Shekarchizadeh on LinkedIn" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/pooyash1998/",
    );
    expect(within(team).getByRole("link", { name: "Anastasia Koslova on LinkedIn" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/anastasia-koslova-a329091b7/",
    );
    expect(within(team).getByRole("link", { name: "Tim Gaydoul on LinkedIn" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/tim-gaydoul-048788174/",
    );
    expect(within(team).getByRole("link", { name: "Ben Theurich on LinkedIn" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/ben-theurich/",
    );
    expect(team).toHaveTextContent(
      "Built with FLUX by Black Forest Labs for artwork and OpenAI for story generation.",
    );
  });
});
