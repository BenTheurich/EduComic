import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronLeft, Download, Loader2, ZoomIn, LayoutGrid, List } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import api from "@/lib/api";
import type { PanelRegenerationStatus } from "@/lib/api";
import { exportStoryPdf } from "@/lib/exportStoryPdf";
import { clampReaderScale } from "@/lib/utils";
import type { Chapter, ChapterWithPanels, Panel } from "@/types/story";

type CorrectionOutcome = "editing" | "working" | "failed" | "unknown" | "published";

interface CorrectionAttempt {
  idempotencyKey: string;
  runId?: string;
}

const StoryViewer = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [chapter, setChapter] = useState<ChapterWithPanels | null>(null);
  const [panels, setPanels] = useState<Panel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [allChapters, setAllChapters] = useState<Chapter[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [correctionPanel, setCorrectionPanel] = useState<number | null>(null);
  const [correction, setCorrection] = useState("");
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [correctionOutcome, setCorrectionOutcome] = useState<CorrectionOutcome>("editing");
  const [correctionAttempt, setCorrectionAttempt] = useState<CorrectionAttempt | null>(null);
  const [exportSettings, setExportSettings] = useState({
    pageSize: "a4",
    layout: "2"
  });

  // Layout mode: 'webtoon' (vertical) or 'grid' (grid layout)
  const [layoutMode, setLayoutMode] = useState<'webtoon' | 'grid'>(() => {
    const saved = localStorage.getItem('teacherStoryReaderLayout');
    return (saved as 'webtoon' | 'grid') || 'webtoon';
  });

  const [imageScale, setImageScale] = useState(() => clampReaderScale(localStorage.getItem('teacherStoryReaderImageScale')));

  // Load chapter data from API
  useEffect(() => {
    const loadChapter = async () => {
      if (!id) return;

      setIsLoading(true);
      setLoadError(null);
      setChapter(null);
      setPanels([]);
      try {
        const response = await api.chapters.getById(id);
        if (response.chapter.status !== "ready") {
          setLoadError(`This chapter is ${response.chapter.status.replaceAll("_", " ")} and cannot be viewed yet.`);
          return;
        }
        setChapter(response.chapter);
        setPanels(response.chapter.panels || []);

        // Load all chapters for this classroom to enable navigation
        if (response.chapter.classroom_id) {
          try {
            const chaptersResponse = await api.classrooms.getChapters(response.chapter.classroom_id);
            if (chaptersResponse.success && chaptersResponse.chapters) {
              // Sort chapters by created_at descending (newest first)
              const sortedChapters = chaptersResponse.chapters
                .filter(chapter => chapter.status === "ready")
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
              setAllChapters(sortedChapters);
              
              // Find current chapter index
              const index = sortedChapters.findIndex(ch => ch.id === id);
              setCurrentIndex(index);
            }
          } catch {
            // The current chapter remains readable without adjacent-story navigation.
          }
        }
      } catch {
        setLoadError("Failed to load this chapter. Please try again.");
        toast.error("Failed to load chapter");
      } finally {
        setIsLoading(false);
      }
    };

    loadChapter();
  }, [id]);

  // Save image scale preference
  useEffect(() => {
    localStorage.setItem('teacherStoryReaderImageScale', imageScale.toString());
  }, [imageScale]);

  // Save layout mode preference
  useEffect(() => {
    localStorage.setItem('teacherStoryReaderLayout', layoutMode);
  }, [layoutMode]);

  const handleExport = async () => {
    if (!chapter || panels.length === 0) {
      toast.error("No panels to export");
      return;
    }

    try {
      toast.info("Generating PDF...");

      const title = chapter.story_title || `Chapter ${chapter.index}`;
      await exportStoryPdf({
        panels,
        title,
        pageSize: exportSettings.pageSize as "a4" | "letter",
        panelsPerPage: Number(exportSettings.layout) as 2 | 4,
      });

      toast.success("PDF downloaded successfully!");
    } catch {
      toast.error("Failed to generate PDF. Please try again.");
    }
  };

  const refreshPublishedPanel = async (panel: Panel) => {
    if (!chapter) return;
    setIsRegenerating(true);
    try {
      const refreshed = await api.chapters.getById(chapter.id);
      setChapter(refreshed.chapter);
      setPanels(refreshed.chapter.panels || []);
      setCorrectionPanel(null);
      setCorrection("");
      setCorrectionAttempt(null);
      setCorrectionOutcome("editing");
      toast.success(`Panel ${panel.index} regenerated`);
    } catch {
      setCorrectionOutcome("published");
    } finally {
      setIsRegenerating(false);
    }
  };

  const handlePanelRegeneration = async (panel: Panel, resume = false) => {
    if (!chapter || !correction.trim()) return;
    let attempt = resume ? correctionAttempt : null;
    if (!attempt) {
      attempt = { idempotencyKey: crypto.randomUUID() };
      setCorrectionAttempt(attempt);
    }
    setIsRegenerating(true);
    setCorrectionOutcome("working");
    try {
      let run: PanelRegenerationStatus;
      if (resume && attempt.runId) {
        run = await api.chapters.getPanelRegeneration(attempt.runId);
      } else {
        run = await api.chapters.regeneratePanel(
          chapter.id,
          panel.index,
          chapter.revision,
          correction,
          attempt.idempotencyKey,
        );
      }
      attempt = { ...attempt, runId: run.run_id };
      setCorrectionAttempt(attempt);
      for (let poll = 0; run.status === "regenerating" && poll < 300; poll += 1) {
        await new Promise(resolve => setTimeout(resolve, 400));
        run = await api.chapters.getPanelRegeneration(run.run_id);
      }
      if (run.status === "regenerating") {
        setCorrectionOutcome("unknown");
        return;
      }
      if (run.status === "failed") {
        setCorrectionAttempt(null);
        setCorrectionOutcome("failed");
        return;
      }
      setCorrectionOutcome("published");
      await refreshPublishedPanel(panel);
    } catch {
      setCorrectionOutcome("unknown");
    } finally {
      setIsRegenerating(false);
    }
  };

  const renderPanel = (panel: Panel, grid: boolean) => (
    <div key={panel.id} className={grid ? "overflow-hidden rounded-lg bg-white shadow-sm" : "w-full bg-white"}>
      <img
        src={panel.image}
        alt={`Panel ${panel.index}`}
        className="block h-auto w-full"
        loading="lazy"
      />
      <div className="space-y-3 p-3 text-left leading-normal">
        {correctionPanel !== panel.index ? (
          <Button
            aria-label={`Correct panel ${panel.index}`}
            variant="outline"
            size="sm"
            disabled={isRegenerating || correctionOutcome === "unknown" || correctionOutcome === "published"}
            onClick={() => {
              setCorrectionPanel(panel.index);
              setCorrection("");
              setCorrectionAttempt(null);
              setCorrectionOutcome("editing");
            }}
          >
            Correct panel {panel.index}
          </Button>
        ) : (
          <>
            <Label htmlFor={`panel-correction-${panel.index}`}>Correction for panel {panel.index}</Label>
            <Textarea
              id={`panel-correction-${panel.index}`}
              value={correction}
              maxLength={500}
              disabled={isRegenerating || correctionOutcome === "unknown" || correctionOutcome === "published"}
              onChange={event => setCorrection(event.target.value)}
              placeholder="Describe the visual correction for this panel"
            />
            {isRegenerating && <p role="status">Regenerating panel {panel.index}...</p>}
            {correctionOutcome === "failed" && (
              <p role="alert" className="text-sm text-destructive">
                Panel {panel.index} could not be regenerated. The previous panel is still available.
              </p>
            )}
            {correctionOutcome === "unknown" && (
              <p role="alert" className="text-sm text-destructive">
                Panel {panel.index} regeneration status could not be confirmed. Check the existing attempt before trying again.
              </p>
            )}
            {correctionOutcome === "published" && (
              <p role="alert" className="text-sm text-destructive">
                Panel {panel.index} correction completed, but the story could not be refreshed.
              </p>
            )}
            <div className="flex gap-2">
              <Button
                aria-label={
                  correctionOutcome === "published"
                    ? "Reload story"
                    : correctionOutcome === "unknown"
                      ? `Check panel ${panel.index} status`
                      : `${correctionOutcome === "failed" ? "Retry" : "Regenerate"} panel ${panel.index}`
                }
                size="sm"
                disabled={isRegenerating || !correction.trim()}
                onClick={() => {
                  if (correctionOutcome === "published") void refreshPublishedPanel(panel);
                  else void handlePanelRegeneration(panel, correctionOutcome === "unknown");
                }}
              >
                {isRegenerating
                  ? "Regenerating..."
                  : correctionOutcome === "published"
                    ? "Reload story"
                    : correctionOutcome === "unknown"
                      ? "Check status"
                      : correctionOutcome === "failed"
                        ? "Retry"
                        : "Regenerate"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={isRegenerating || correctionOutcome === "unknown" || correctionOutcome === "published"}
                onClick={() => {
                  setCorrectionPanel(null);
                  setCorrectionAttempt(null);
                  setCorrectionOutcome("editing");
                }}
              >
                Cancel
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center space-y-4">
          <Loader2 className="w-16 h-16 text-primary animate-spin mx-auto" />
          <p className="text-muted-foreground">Loading chapter...</p>
        </div>
      </div>
    );
  }

  if (loadError || !chapter) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center space-y-4">
          <p role="alert" className="text-muted-foreground">{loadError || "Chapter not found"}</p>
          <Button onClick={() => navigate(-1)}>Go Back</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/90 shadow-sm backdrop-blur-lg">
            <div className="container mx-auto px-4 py-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="flex-shrink-0">
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Back
                  </Button>
                  <h1 className="text-lg font-semibold text-foreground truncate">
                    {chapter?.story_title || `Chapter ${chapter?.index}`}
                  </h1>
                </div>

                <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button size="sm" variant="outline">
                        <Download className="w-4 h-4 mr-2" />
                        Export PDF
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Export as PDF</DialogTitle>
                        <DialogDescription>Configure your PDF export settings</DialogDescription>
                      </DialogHeader>
                      <div className="space-y-6 py-4">
                        <div className="space-y-3">
                          <Label>Page Size</Label>
                          <RadioGroup value={exportSettings.pageSize} onValueChange={(v) => setExportSettings({ ...exportSettings, pageSize: v })}>
                            <div className="flex items-center space-x-2">
                              <RadioGroupItem value="a4" id="a4" />
                              <Label htmlFor="a4">A4</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <RadioGroupItem value="letter" id="letter" />
                              <Label htmlFor="letter">Letter</Label>
                            </div>
                          </RadioGroup>
                        </div>
                        <div className="space-y-3">
                          <Label>Layout</Label>
                          <RadioGroup value={exportSettings.layout} onValueChange={(v) => setExportSettings({ ...exportSettings, layout: v })}>
                            <div className="flex items-center space-x-2">
                              <RadioGroupItem value="2" id="2panel" />
                              <Label htmlFor="2panel">2 panels per page</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <RadioGroupItem value="4" id="4panel" />
                              <Label htmlFor="4panel">4 panels per page</Label>
                            </div>
                          </RadioGroup>
                        </div>
                        <Button onClick={handleExport} className="w-full">
                          <Download className="w-4 h-4 mr-2" />
                          Download PDF
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>

                  <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-lg border border-border/30">
                    <Button aria-label="Vertical layout" aria-pressed={layoutMode === 'webtoon'} variant={layoutMode === 'webtoon' ? 'default' : 'ghost'} size="sm" onClick={() => setLayoutMode('webtoon')}>
                      <List className="w-4 h-4" />
                    </Button>
                    <Button aria-label="Grid layout" aria-pressed={layoutMode === 'grid'} variant={layoutMode === 'grid' ? 'default' : 'ghost'} size="sm" onClick={() => setLayoutMode('grid')}>
                      <LayoutGrid className="w-4 h-4" />
                    </Button>
                  </div>

                  <ZoomIn aria-hidden="true" className="w-4 h-4 text-muted-foreground" />
                  <div className="flex min-w-40 flex-1 items-center gap-2 sm:flex-none">
                    <Slider aria-label="Image size" aria-valuetext={`${imageScale} percent`} value={[imageScale]} onValueChange={(value) => setImageScale(value[0])} min={10} max={100} step={5} className="flex-1" />
                    <span className="text-sm text-muted-foreground w-10 text-right">{imageScale}%</span>
                  </div>
                </div>
              </div>

              {allChapters.length > 1 && (
                <div className="flex justify-between mt-3 pt-3 border-t">
                  <Button variant="outline" size="sm" onClick={() => { if (currentIndex < allChapters.length - 1) navigate(`/teacher/story/${allChapters[currentIndex + 1].id}`); }} disabled={currentIndex === -1 || currentIndex >= allChapters.length - 1}>
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Previous Story
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => { if (currentIndex > 0) navigate(`/teacher/story/${allChapters[currentIndex - 1].id}`); }} disabled={currentIndex === -1 || currentIndex <= 0}>
                    Next Story
                    <ChevronLeft className="w-4 h-4 ml-1 rotate-180" />
                  </Button>
                </div>
              )}
            </div>
      </header>

      {layoutMode === 'webtoon' ? (
        <div className="flex flex-col items-center" style={{ width: `${imageScale}%`, margin: '0 auto' }}>
          {panels.length === 0 ? (
            <div className="text-center py-24">
              <div className="text-8xl mb-4">📚</div>
              <p className="text-muted-foreground text-lg">No panels yet</p>
            </div>
          ) : (
            [...panels].sort((a, b) => a.index - b.index).map((panel) => renderPanel(panel, false))
          )}
        </div>
      ) : (
        <div className="container mx-auto px-4 pb-8">
          {panels.length === 0 ? (
            <div className="text-center py-24">
              <div className="text-8xl mb-4">📚</div>
              <p className="text-muted-foreground text-lg">No panels yet</p>
            </div>
          ) : (
            <div className={`grid gap-4 ${imageScale <= 30 ? 'grid-cols-2 md:grid-cols-3 lg:grid-cols-5' : imageScale <= 50 ? 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4' : imageScale <= 80 ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : imageScale <= 120 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
              {[...panels].sort((a, b) => a.index - b.index).map((panel) => renderPanel(panel, true))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StoryViewer;
