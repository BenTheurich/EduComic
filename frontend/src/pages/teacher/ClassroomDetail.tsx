import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft, Copy, Plus, CheckCircle, Clock, Filter, Loader2, Grid3x3, List, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { exportStoryPdf } from "@/lib/exportStoryPdf";
import type { Chapter } from "@/types/story";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface Student {
  id: string;
  name: string;
  interests: string;
  avatar_url: string | null;
  photo_url: string | null;
  status: "pending" | "generated";
}

interface Classroom {
  id: string;
  name: string;
  subject: string;
  grade_level: string;
  story_theme: string;
  design_style: string;
}

const ClassroomDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [classroom, setClassroom] = useState<Classroom | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [storySortBy, setStorySortBy] = useState<"week" | "date">("week");
  const [studentViewMode, setStudentViewMode] = useState<"grid" | "list">("grid");

  useEffect(() => {
    const fetchClassroomData = async () => {
      if (!id) return;

      try {
        setIsLoading(true);

        // Fetch classroom with students
        const classroomResponse = await api.classrooms.getById(id);
        setClassroom(classroomResponse.classroom);

        // Map students and add status based on avatar_url
        const studentsWithStatus = classroomResponse.classroom.students.map(student => {
          console.log(`Student ${student.name}:`, {
            hasPhoto: !!student.photo_url,
            hasAvatar: !!student.avatar_url,
            avatarUrl: student.avatar_url?.substring(0, 50) + '...'
          });
          return {
            ...student,
            status: student.avatar_url ? "generated" as const : "pending" as const
          };
        });
        setStudents(studentsWithStatus);

        // Fetch chapters
        const chaptersResponse = await api.classrooms.getChapters(id);
        setChapters(chaptersResponse.chapters);

      } catch (error) {
        console.error("Failed to fetch classroom data:", error);
        toast.error("Failed to load classroom data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchClassroomData();
  }, [id]);

  // Get tab from URL or default to stories
  const currentTab = searchParams.get('tab') || 'stories';

  // Update URL when tab changes
  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value });
  };

  const copyInviteLink = () => {
    const link = `${window.location.origin}/student/join/${id}`;
    navigator.clipboard.writeText(link);
    toast.success("Invite link copied to clipboard!");
  };

  // Get calendar week from date
  const getWeek = (date: Date) => {
    const onejan = new Date(date.getFullYear(), 0, 1);
    const millisecsInDay = 86400000;
    return Math.ceil((((date.getTime() - onejan.getTime()) / millisecsInDay) + onejan.getDay() + 1) / 7);
  };

  // Export chapter as PDF
  const handleExportPDF = async (chapterId: string, chapterTitle: string) => {
    try {
      toast.info("Generating PDF...");

      // Fetch chapter with panels
      const response = await api.chapters.getById(chapterId);
      const panels = response.chapter.panels || [];

      if (panels.length === 0) {
        toast.error("No panels to export");
        return;
      }

      await exportStoryPdf({ panels, title: chapterTitle });
      toast.success("PDF downloaded successfully!");
    } catch (error) {
      console.error("PDF export failed:", error);
      toast.error("Failed to generate PDF. Please try again.");
    }
  };

  // Delete chapter
  const handleDeleteChapter = async (chapterId: string, chapterTitle: string) => {
    try {
      toast.info("Deleting chapter...");
      
      await api.chapters.delete(chapterId);
      
      // Remove from local state
      setChapters(chapters.filter(ch => ch.id !== chapterId));
      
      toast.success(`"${chapterTitle}" deleted successfully!`);
    } catch (error) {
      console.error("Failed to delete chapter:", error);
      toast.error("Failed to delete chapter. Please try again.");
    }
  };

  // Group chapters by week or keep sorted by date
  const groupedChapters = () => {
    if (storySortBy === "date") {
      return [{
        label: "All Stories", chapters: [...chapters].sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
      }];
    }

    const groups: { [key: string]: Chapter[] } = {};
    chapters.forEach(chapter => {
      const date = new Date(chapter.created_at);
      const week = getWeek(date);
      const year = date.getFullYear();
      const key = `KW ${week} ${year}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(chapter);
    });

    return Object.entries(groups)
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([label, chapters]) => ({ label, chapters }));
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-16 h-16 text-primary animate-spin mx-auto" />
          <p className="text-muted-foreground">Loading classroom...</p>
        </div>
      </div>
    );
  }

  if (!classroom) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-muted-foreground">Classroom not found</p>
          <Button onClick={() => navigate("/teacher/dashboard")}>
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      {/* Header - Glass Effect */}
      <header className="sticky top-0 z-20 backdrop-blur-lg bg-background/70 border-b border-border/50">
        <div className="container mx-auto px-4 py-4">
          <Button variant="ghost" onClick={() => navigate("/teacher/dashboard")}>
            <ChevronLeft className="w-5 h-5 mr-2" />
            Back to Dashboard
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Classroom Header - Glass Effect */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="flex-1">
              <h1 className="text-4xl font-bold text-foreground mb-2">
                {classroom.name}
              </h1>
              <div className="flex gap-2 flex-wrap mb-3">
                <Badge className="bg-blue-500/80 backdrop-blur-sm text-white border-blue-300/30">{classroom.subject}</Badge>
                <Badge className="backdrop-blur-sm bg-background/60 border-border/50" variant="outline">Grade {classroom.grade_level}</Badge>
                <Badge className="backdrop-blur-sm bg-background/60 border-border/50" variant="outline">{classroom.story_theme}</Badge>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>Invite students:</span>
                <code className="px-2 py-1 bg-muted/50 backdrop-blur-sm rounded text-xs font-mono border border-border/30">
                  {window.location.origin}/student/join/{id}
                </code>
                <Button
                  onClick={copyInviteLink}
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 backdrop-blur-sm"
                >
                  <Copy className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Tabs - Glass Effect */}
        <Tabs value={currentTab} onValueChange={handleTabChange} className="space-y-6">
          <TabsList className="backdrop-blur-lg bg-muted/50 border border-border/30">
            <TabsTrigger value="students">Students</TabsTrigger>
            <TabsTrigger value="stories">Stories</TabsTrigger>
          </TabsList>

          <TabsContent value="students" className="space-y-6">
            {students.length === 0 ? (
              <Card className="backdrop-blur-lg bg-card/70 border-border/50">
                <CardContent className="pt-12 pb-12 text-center space-y-4">
                  <p className="text-muted-foreground">
                    No students yet. Share the invite link to get started.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* View Toggle */}
                <div className="flex justify-end">
                  <div className="flex gap-1 p-1 backdrop-blur-lg bg-muted/50 rounded-lg border border-border/30">
                    <Button
                      variant={studentViewMode === "grid" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setStudentViewMode("grid")}
                      className="backdrop-blur-sm"
                    >
                      <Grid3x3 className="w-4 h-4 mr-2" />
                      Grid
                    </Button>
                    <Button
                      variant={studentViewMode === "list" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setStudentViewMode("list")}
                      className="backdrop-blur-sm"
                    >
                      <List className="w-4 h-4 mr-2" />
                      List
                    </Button>
                  </div>
                </div>

                {/* Grid View */}
                {studentViewMode === "grid" && (
                  <motion.div
                    className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                  >
                    {students.map((student, idx) => (
                      <motion.div
                        key={student.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: idx * 0.1 }}
                      >
                        <Card className="backdrop-blur-lg bg-card/70 border-border/50 hover:bg-card/80 transition-all hover:shadow-xl h-full">
                          <CardContent className="pt-6 pb-6 flex flex-col h-full">
                            {/* Student Photo - Fixed Height */}
                            <div className="flex justify-center mb-4">
                              <div className="relative">
                                <Avatar className="w-24 h-24 border-4 border-border/30">
                                  <AvatarImage
                                    src={student.photo_url || student.avatar_url || undefined}
                                    alt={student.name}
                                    className="object-cover"
                                  />
                                  <AvatarFallback className="bg-primary/20 text-2xl">
                                    {student.name.split(' ').map(n => n[0]).join('')}
                                  </AvatarFallback>
                                </Avatar>
                                {student.avatar_url && student.photo_url && (
                                  <div className="absolute -bottom-2 -right-2 w-12 h-12 rounded-full border-3 border-background overflow-hidden bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
                                    <Avatar className="w-full h-full">
                                      <AvatarImage
                                        src={student.avatar_url}
                                        alt={`${student.name} avatar`}
                                        className="object-cover"
                                      />
                                      <AvatarFallback className="bg-gradient-to-br from-purple-500 to-pink-500 text-white text-xs font-bold">
                                        🎨
                                      </AvatarFallback>
                                    </Avatar>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Student Info - Fixed Height */}
                            <div className="text-center flex-1 flex flex-col">
                              <h3 className="font-semibold text-foreground text-lg mb-2 min-h-[28px]">
                                {student.name}
                              </h3>
                              {/* Exactly 2 lines for interests - Fixed Height */}
                              <p className="text-sm text-muted-foreground line-clamp-2 mb-4 h-[40px] leading-[20px]">
                                {student.interests}
                              </p>
                            </div>

                            {/* Status Badge - Fixed at Bottom */}
                            <Badge
                              className={`w-full justify-center ${student.status === "generated"
                                ? "bg-green-500/80 text-white backdrop-blur-sm border-green-300/30"
                                : "bg-amber-500/80 text-white backdrop-blur-sm border-amber-300/30"
                                }`}
                            >
                              {student.status === "generated" ? (
                                <>
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  Avatar Generated
                                </>
                              ) : (
                                <>
                                  <Clock className="w-3 h-3 mr-1" />
                                  Avatar Pending
                                </>
                              )}
                            </Badge>
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))}
                  </motion.div>
                )}

                {/* List View */}
                {studentViewMode === "list" && (
                  <motion.div
                    className="space-y-3"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                  >
                    {students.map((student, idx) => (
                      <motion.div
                        key={student.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: idx * 0.05 }}
                      >
                        <Card className="backdrop-blur-lg bg-card/70 border-border/50 hover:bg-card/80 transition-all hover:shadow-lg">
                          <CardContent className="py-4">
                            <div className="flex items-center gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3">
                                  <h3 className="font-semibold text-foreground text-lg">{student.name}</h3>
                                  <Badge
                                    className={student.status === "generated"
                                      ? "bg-green-500/80 text-white backdrop-blur-sm border-green-300/30"
                                      : "bg-amber-500/80 text-white backdrop-blur-sm border-amber-300/30"
                                    }
                                  >
                                    {student.status === "generated" ? (
                                      <>
                                        <CheckCircle className="w-3 h-3 mr-1" />
                                        Avatar Generated
                                      </>
                                    ) : (
                                      <>
                                        <Clock className="w-3 h-3 mr-1" />
                                        Avatar Pending
                                      </>
                                    )}
                                  </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                                  {student.interests}
                                </p>
                              </div>

                              {student.avatar_url && (
                                <div className="flex-shrink-0">
                                  <div className="w-12 h-12 rounded-lg border-2 border-border/30 overflow-hidden">
                                    <img
                                      src={student.avatar_url}
                                      alt={`${student.name} avatar`}
                                      className="w-full h-full object-cover"
                                    />
                                  </div>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </>
            )}
          </TabsContent>

          <TabsContent value="stories" className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between gap-4">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-muted-foreground" />
                <Select value={storySortBy} onValueChange={(value: "week" | "date") => setStorySortBy(value)}>
                  <SelectTrigger className="w-[180px] backdrop-blur-sm bg-background/60">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="week">By Week</SelectItem>
                    <SelectItem value="date">By Date</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button asChild className="backdrop-blur-sm">
                <a href={`/teacher/classroom/${id}/story/new`}>
                  <Plus className="w-4 h-4 mr-2" />
                  Generate New Story
                </a>
              </Button>
            </div>

            {chapters.length === 0 ? (
              <Card className="backdrop-blur-lg bg-card/70 border-border/50">
                <CardContent className="pt-12 pb-12 text-center space-y-4">
                  <p className="text-muted-foreground">
                    No stories yet. Generate your first story based on a lesson!
                  </p>
                  <Button asChild className="backdrop-blur-sm">
                    <a href={`/teacher/classroom/${id}/story/new`}>
                      <Plus className="w-4 h-4 mr-2" />
                      Generate Story
                    </a>
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-8">
                {groupedChapters().map((group, groupIdx) => (
                  <div key={group.label} className="space-y-4">
                    <h3 className="text-lg font-semibold text-foreground/80 backdrop-blur-sm">
                      {group.label}
                    </h3>
                    {group.chapters.map((chapter, idx) => (
                      <motion.div
                        key={chapter.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: (groupIdx * 0.1) + (idx * 0.05) }}
                      >
                        <Card className="backdrop-blur-lg bg-card/70 border-border/50 hover:bg-card/80 transition-all hover:shadow-xl h-full">
                          <CardContent className="pt-6 h-full">
                            <div className="flex flex-col md:flex-row gap-4 h-full">
                              <div className="w-full md:w-32 h-32 md:h-auto bg-muted/50 backdrop-blur-sm rounded-lg flex items-center justify-center border border-border/30 overflow-hidden flex-shrink-0">
                                {chapter.thumbnail_url ? (
                                  <img
                                    src={chapter.thumbnail_url}
                                    alt={`Chapter ${chapter.index}`}
                                    className="w-full h-full object-cover"
                                  />
                                ) : (
                                  <span className="text-4xl">📚</span>
                                )}
                              </div>
                              <div className="flex-1 flex flex-col justify-between space-y-3 min-h-[180px]">
                                <div className="flex-1">
                                  <h3 className="text-xl font-bold text-foreground line-clamp-1">{chapter.story_title || `Chapter ${chapter.index}`}</h3>
                                  <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                                    {chapter.chapter_outline || chapter.original_prompt}
                                  </p>
                                  <p className="text-xs text-muted-foreground mt-2">
                                    Created on {new Date(chapter.created_at).toLocaleDateString()}
                                  </p>
                                  <div className="mt-2">
                                    <Badge
                                      variant={chapter.status === "ready" ? "default" : chapter.status === "failed" ? "destructive" : "outline"}
                                      className="capitalize"
                                    >
                                      {chapter.status === "ready" && <CheckCircle className="w-3 h-3 mr-1" />}
                                      {chapter.status.replaceAll("_", " ")}
                                    </Badge>
                                  </div>
                                </div>
                                <div className="flex gap-2 flex-wrap">
                                  {chapter.status === "ready" && (
                                    <>
                                      <Button asChild variant="default" className="backdrop-blur-sm">
                                        <a href={`/teacher/story/${chapter.id}`}>View Chapter</a>
                                      </Button>
                                      <Button
                                        variant="outline"
                                        className="backdrop-blur-sm bg-background/60"
                                        onClick={() => handleExportPDF(chapter.id, chapter.story_title || `Chapter ${chapter.index}`)}
                                      >
                                        Export PDF
                                      </Button>
                                    </>
                                  )}
                                  <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                      <Button
                                        variant="destructive"
                                        size="icon"
                                        className="backdrop-blur-sm"
                                      >
                                        <Trash2 className="w-4 h-4" />
                                      </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                      <AlertDialogHeader>
                                        <AlertDialogTitle>Delete Chapter?</AlertDialogTitle>
                                        <AlertDialogDescription>
                                          Are you sure you want to delete "{chapter.story_title || `Chapter ${chapter.index}`}"? 
                                          This will permanently delete the chapter and all its panels. This action cannot be undone.
                                        </AlertDialogDescription>
                                      </AlertDialogHeader>
                                      <AlertDialogFooter>
                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                        <AlertDialogAction
                                          onClick={() => handleDeleteChapter(chapter.id, chapter.story_title || `Chapter ${chapter.index}`)}
                                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                        >
                                          Delete
                                        </AlertDialogAction>
                                      </AlertDialogFooter>
                                    </AlertDialogContent>
                                  </AlertDialog>
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

        </Tabs>
      </div>
    </div>
  );
};

export default ClassroomDetail;
