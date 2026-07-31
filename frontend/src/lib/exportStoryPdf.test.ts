import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Panel } from "@/types/story";
import { exportStoryPdf } from "./exportStoryPdf";

const { addImage, save } = vi.hoisted(() => ({
  addImage: vi.fn(),
  save: vi.fn(),
}));

vi.mock("jspdf", () => ({
  jsPDF: class {
    internal = { pageSize: { getWidth: () => 210, getHeight: () => 297 } };
    addImage = addImage;
    addPage = vi.fn();
    save = save;
  },
}));

const panel = (index: number): Panel => ({
  id: `panel-${index}`,
  chapter_id: "chapter-1",
  index,
  image: `https://cdn.example.invalid/panel-${index}.png`,
  created_at: "2026-07-31T00:00:00Z",
});

const png = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 1]);

describe("exportStoryPdf", () => {
  beforeEach(() => {
    addImage.mockReset();
    save.mockReset();
  });

  afterEach(() => vi.unstubAllGlobals());

  it("embeds verified remote image bytes before saving", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "image/png" }),
      arrayBuffer: () => Promise.resolve(png.buffer),
    }));

    await exportStoryPdf({ panels: [panel(1)], title: "Safe story" });

    expect(addImage.mock.calls[0][0]).toEqual(png);
    expect(addImage.mock.calls[0][1]).toBe("PNG");
    expect(save).toHaveBeenCalledWith("Safe story.pdf");
  });

  it.each([
    ["failed response", { ok: false, headers: new Headers(), arrayBuffer: vi.fn() }],
    ["invalid image", {
      ok: true,
      headers: new Headers({ "content-type": "image/png" }),
      arrayBuffer: () => Promise.resolve(new Uint8Array([1, 2, 3]).buffer),
    }],
    ["unsupported image type", {
      ok: true,
      headers: new Headers({ "content-type": "image/svg+xml" }),
      arrayBuffer: () => Promise.resolve(png.buffer),
    }],
  ])("rejects a %s without saving", async (_case, response) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(exportStoryPdf({ panels: [panel(1)], title: "Unsafe story" })).rejects.toThrow();

    expect(addImage).not.toHaveBeenCalled();
    expect(save).not.toHaveBeenCalled();
  });
});
