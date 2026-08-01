import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Panel } from "@/types/story";

interface StoryOption {
  id: string;
  title: string;
  theme: string;
  summary: string;
}

const StoryGenerator = () => {
  const navigate = useNavigate();
  const { classroomId } = useParams<{ classroomId: string }>();
  const [step, setStep] = useState(1);
  const [lessonInput, setLessonInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [storyOptions, setStoryOptions] = useState<StoryOption[]>([]);
  const [selectedStory, setSelectedStory] = useState<string | null>(null);
  const [chapterId, setChapterId] = useState<string | null>(null);
  const [classroom, setClassroom] = useState<{ name: string; subject: string; grade_level: string } | null>(null);
  const [classroomLoadError, setClassroomLoadError] = useState<string | null>(null);
  const [classroomReloadKey, setClassroomReloadKey] = useState(0);
  const [panels, setPanels] = useState<Panel[]>([]);
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const generationRequestRef = useRef<{ chapterId: string; storyId: string; idempotencyKey: string } | null>(null);
  const pollAttempts = useRef(0);
  const consecutivePollingErrors = useRef(0);
  const maxPollAttempts = 300; // 10 minutes at 2-second intervals

  // Fetch classroom data on mount
  useEffect(() => {
    if (classroomId) {
      setClassroomLoadError(null);
      api.classrooms.getById(classroomId)
        .then(response => {
          if (response.success && response.classroom) {
            setClassroom({
              name: response.classroom.name,
              subject: response.classroom.subject,
              grade_level: response.classroom.grade_level
            });
          } else {
            setClassroomLoadError("Failed to load classroom details. Please try again.");
          }
        })
        .catch(() => {
          setClassroomLoadError("Failed to load classroom details. Please try again.");
        });
    }
  }, [classroomId, classroomReloadKey]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const pollPanelsProgress = async () => {
    if (!chapterId) return;

    try {
      const response = await api.chapters.getById(chapterId);
      consecutivePollingErrors.current = 0;
      pollAttempts.current += 1;
      if (response.success && response.chapter) {
        const chapterPanels = response.chapter.panels || [];
        setPanels(chapterPanels);

        // Check if generation is complete
        if (response.chapter.status === 'ready') {
          generationRequestRef.current = null;
          setIsPolling(false);
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
          toast.success("Story chapter created!");
          setTimeout(() => {
            navigate(`/teacher/classroom/${classroomId}`);
          }, 1000);
          return;
        }

        if (response.chapter.status === 'failed') {
          generationRequestRef.current = null;
          setIsPolling(false);
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
          setGenerationError("Story generation failed. Try another story or retry your lesson.");
          return;
        }
      }

      // Timeout after max attempts
      if (pollAttempts.current >= maxPollAttempts) {
        setIsPolling(false);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
        toast.error("Generation is taking longer than expected. You can check back later.");
      }
    } catch {
      consecutivePollingErrors.current += 1;

      // Stop after too many errors
      if (consecutivePollingErrors.current >= 10) {
        setIsPolling(false);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
        const message = "Lost connection to server. Generation may still be in progress.";
        setGenerationError(message);
        toast.error(message);
      }
    }
  };

  const startPolling = () => {
    setIsPolling(true);
    pollAttempts.current = 0;
    consecutivePollingErrors.current = 0;
    setGenerationError(null);
    setPanels([]);

    // Initial poll
    pollPanelsProgress();

    // Poll every 2 seconds
    pollingIntervalRef.current = setInterval(() => {
      pollPanelsProgress();
    }, 2000);
  };

  const generateOptions = async () => {
    if (!classroomId) {
      toast.error("No classroom selected");
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);
    try {
      // Start chapter and generate story options
      const response = await api.story.startChapter(classroomId, lessonInput);

      setChapterId(response.chapter.id);
      generationRequestRef.current = null;
      const options = response.chapter.story_ideas || [];
      setStoryOptions(options);
      setStep(2);
      toast.success("Story options generated!");

    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate story options";
      setGenerationError(message);
      toast.error(message);
    } finally {
      setIsGenerating(false);
    }
  };

  const selectStory = async (storyId: string) => {
    if (!chapterId) {
      toast.error("No chapter found");
      return;
    }

    setSelectedStory(storyId);
    setGenerationError(null);
    setStep(3);
    const previousRequest = generationRequestRef.current;
    const request = previousRequest?.chapterId === chapterId && previousRequest.storyId === storyId
      ? previousRequest
      : { chapterId, storyId, idempotencyKey: crypto.randomUUID() };
    generationRequestRef.current = request;

    try {
      await api.story.chooseIdea(chapterId, storyId);

      // Start the comic generation in the background
      await api.story.commitChapter(chapterId, storyId, request.idempotencyKey);

      // Start polling for panels
      startPolling();
    } catch {
      toast.error("Failed to start comic generation");
      setStep(2); // Go back to selection
    }
  };

  return (
    <div className="min-h-screen bg-muted/20">
      {/* Header */}
      <header className="bg-background border-b">
        <div className="container mx-auto px-4 py-4">
          <Button variant="ghost" onClick={() => navigate(-1)}>
            <ChevronLeft className="w-5 h-5 mr-2" />
            Back
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <div className="space-y-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Generate New Story</h1>
            {classroom && (
              <p className="text-muted-foreground">
                {classroom.subject} • {classroom.grade_level}
              </p>
            )}
          </div>

          {classroomLoadError && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <p role="alert" className="text-sm text-destructive">{classroomLoadError}</p>
              <Button
                variant="outline"
                onClick={() => setClassroomReloadKey((key) => key + 1)}
              >
                Retry classroom details
              </Button>
            </div>
          )}

          {step === 1 && (
            <Card>
              <CardContent className="pt-6 space-y-6">
                <div className="space-y-3">
                  <label className="text-sm font-medium text-foreground">
                    What did you teach today? *
                  </label>
                  <Textarea
                    placeholder="Example: Today we covered Newton's Three Laws of Motion. Students learned about force, mass, and acceleration through hands-on experiments with balls and ramps."
                    value={lessonInput}
                    onChange={(e) => setLessonInput(e.target.value)}
                    className="min-h-[200px]"
                    maxLength={500}
                  />
                  <div className="text-xs text-muted-foreground text-right">
                    {lessonInput.length}/500 characters
                  </div>
                </div>

                {generationError && (
                  <p role="alert" className="text-sm text-destructive">
                    {generationError} Please try again.
                  </p>
                )}

                <Button
                  onClick={generateOptions}
                  disabled={!lessonInput || isGenerating}
                  className="w-full"
                  size="lg"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Generating Options...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5 mr-2" />
                      Generate Story Options
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-foreground">Choose Your Story</h2>
              <div className="grid md:grid-cols-3 gap-6">
                {storyOptions.map((option) => (
                  <Card
                    key={option.id}
                    className="cursor-pointer hover:shadow-lg transition-all hover:scale-[1.02] border-2 hover:border-primary"
                    onClick={() => selectStory(option.id)}
                  >
                    <CardContent className="pt-6 space-y-4">
                      <div className="w-full aspect-square rounded-lg overflow-hidden bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                        <span className="text-5xl">{option.theme}</span>
                      </div>
                        
                      {/* Title */}
                      <h3 className="text-lg font-bold text-foreground text-center line-clamp-2 min-h-[3.5rem]">
                        {option.title}
                      </h3>
                        
                      {/* Summary */}
                      <p className="text-sm text-muted-foreground line-clamp-3 min-h-[4rem]">
                        {option.summary}
                      </p>
                        
                      {/* Select Button */}
                      <Button className="w-full">
                        Select This Story
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <Card>
              <CardContent className="pt-12 pb-12 space-y-8">
                {generationError ? (
                  <div className="text-center space-y-4">
                    <p role="alert" className="text-destructive">{generationError}</p>
                    <Button onClick={() => {
                      setGenerationError(null);
                      setSelectedStory(null);
                      setPanels([]);
                      setStep(2);
                    }}>
                      Try another story
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="text-center space-y-4">
                      <Loader2 className="w-16 h-16 mx-auto animate-spin text-primary" />
                      <h2 className="text-2xl font-bold text-foreground">
                        Generating your personalized graphic novel...
                      </h2>
                      <p className="text-muted-foreground">
                        {panels.length} panel{panels.length !== 1 ? 's' : ''} completed
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Progress aria-label="Story generation progress" className="h-3 animate-pulse" />
                      <p className="text-sm text-muted-foreground text-center">
                        This may take a few minutes...
                      </p>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {panels.map((panel) => (
                        <div
                          key={panel.id}
                          className="aspect-square rounded-lg overflow-hidden bg-primary/20 shadow-md"
                        >
                          <img
                            src={panel.image}
                            alt={`Panel ${panel.index}`}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      ))}
                      {isPolling && (
                        <div className="aspect-square rounded-lg bg-muted animate-pulse flex items-center justify-center">
                          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                        </div>
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default StoryGenerator;
