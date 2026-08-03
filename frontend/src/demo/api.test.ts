import { describe, expect, it } from "vitest";
import { demoApiFetch } from "./api";

describe("public demo API", () => {
  it("returns the fictional classroom roster", async () => {
    const response = await demoApiFetch<{ classroom: { students: unknown[] } }>(
      "/classrooms/class-5b-science",
    );

    expect(response.classroom.students).toHaveLength(8);
  });

  it("returns the complete twelve-panel story", async () => {
    const response = await demoApiFetch<{ chapter: { panels: unknown[] } }>(
      "/chapters/misty-jar",
    );

    expect(response.chapter.panels).toHaveLength(12);
  });

  it("never permits writes", async () => {
    await expect(demoApiFetch("/classrooms", { method: "POST" })).rejects.toThrow(
      "The public demo is read-only.",
    );
  });

  it("does not substitute a different student for an unknown profile", async () => {
    await expect(demoApiFetch("/students/not-a-student")).rejects.toThrow(
      "Student not found.",
    );
  });
});
