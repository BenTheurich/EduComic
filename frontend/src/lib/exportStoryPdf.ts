import type { Panel } from "@/types/story";

type ImageFormat = "PNG" | "JPEG";

const imageTypes: Record<string, { format: ImageFormat; valid: (bytes: Uint8Array) => boolean }> = {
  "image/png": {
    format: "PNG",
    valid: (bytes) =>
      bytes.length >= 8 && [137, 80, 78, 71, 13, 10, 26, 10].every((byte, index) => bytes[index] === byte),
  },
  "image/jpeg": {
    format: "JPEG",
    valid: (bytes) => bytes.length >= 3 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255,
  },
};

async function fetchPanel(panel: Panel) {
  const response = await fetch(panel.image, { signal: AbortSignal.timeout(10_000) });
  if (!response.ok) throw new Error(`Panel ${panel.index} image request failed`);

  const mime = response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase() ?? "";
  const imageType = imageTypes[mime];
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!imageType?.valid(bytes)) throw new Error(`Panel ${panel.index} is not a supported image`);

  return { bytes, format: imageType.format };
}

export async function exportStoryPdf({
  panels,
  title,
  pageSize = "a4",
  panelsPerPage = 2,
}: {
  panels: Panel[];
  title: string;
  pageSize?: "a4" | "letter";
  panelsPerPage?: 2 | 4;
}): Promise<void> {
  if (panels.length === 0) throw new Error("No panels to export");

  const sortedPanels = [...panels].sort((a, b) => a.index - b.index);
  const images = await Promise.all(sortedPanels.map(fetchPanel));
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: pageSize });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 10;
  const spacing = 5;
  const usableWidth = pageWidth - 2 * margin;
  const usableHeight = pageHeight - 2 * margin;
  const maxPanelWidth = panelsPerPage === 2 ? usableWidth : (usableWidth - spacing) / 2;
  const maxPanelHeight = (usableHeight - spacing) / 2;
  const panelSize = Math.min(maxPanelWidth, maxPanelHeight);

  images.forEach(({ bytes, format }, index) => {
    if (index > 0 && index % panelsPerPage === 0) doc.addPage();

    const indexOnPage = index % panelsPerPage;
    const row = panelsPerPage === 2 ? indexOnPage : Math.floor(indexOnPage / 2);
    const column = panelsPerPage === 2 ? 0 : indexOnPage % 2;
    const x = margin + column * (maxPanelWidth + spacing) + (maxPanelWidth - panelSize) / 2;
    const y = margin + row * (maxPanelHeight + spacing) + (maxPanelHeight - panelSize) / 2;
    doc.addImage(bytes, format, x, y, panelSize, panelSize);
  });

  doc.save(`${title}.pdf`);
}
