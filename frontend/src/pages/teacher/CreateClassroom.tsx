import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const styles = [
  { id: "manga", name: "Manga" },
  { id: "comic", name: "Comic" },
  { id: "cartoon", name: "Cartoon" },
];

const CreateClassroom = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: "",
    subject: "",
    grade: "",
    customTheme: "",
    style: "",
  });

  const handleSubmit = async () => {
    try {
      await api.classrooms.create({
        name: formData.name,
        subject: formData.subject,
        grade_level: formData.grade,
        story_theme: formData.customTheme,
        design_style: formData.style,
      });
      toast.success("Classroom created successfully!");
      navigate("/teacher/dashboard");
    } catch (error) {
      console.error("Failed to create classroom:", error);
      toast.error("Failed to create classroom. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="bg-background border-b">
        <div className="container mx-auto px-4 py-4">
          <Button variant="ghost" onClick={() => navigate("/teacher/dashboard")}>
            <ChevronLeft className="w-5 h-5 mr-2" />
            Back
          </Button>
        </div>
      </header>

      <div className="container mx-auto px-4 py-12 max-w-3xl">
        <div className="space-y-8">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold text-foreground">Create New Classroom</h1>
            <div className="flex items-center gap-2">
              <div className="text-sm text-muted-foreground">Step {step} of 2</div>
              <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${(step / 2) * 100}%` }}
                />
              </div>
            </div>
          </div>

          <Card>
            <CardContent className="pt-6 space-y-6">
              {step === 1 ? (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Classroom Name *</Label>
                    <Input
                      id="name"
                      placeholder="e.g., Physics 101"
                      value={formData.name}
                      onChange={(event) => setFormData({ ...formData, name: event.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="subject">Subject *</Label>
                    <Select value={formData.subject} onValueChange={(subject) => setFormData({ ...formData, subject })}>
                      <SelectTrigger id="subject">
                        <SelectValue placeholder="Select subject" />
                      </SelectTrigger>
                      <SelectContent>
                        {['physics', 'chemistry', 'biology', 'math', 'english', 'history'].map((subject) => (
                          <SelectItem key={subject} value={subject} className="capitalize">
                            {subject}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="grade">Grade Level *</Label>
                    <Select value={formData.grade} onValueChange={(grade) => setFormData({ ...formData, grade })}>
                      <SelectTrigger id="grade">
                        <SelectValue placeholder="Select grade" />
                      </SelectTrigger>
                      <SelectContent>
                        {[6, 7, 8, 9, 10, 11, 12].map((grade) => (
                          <SelectItem key={grade} value={grade.toString()}>
                            Grade {grade}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    onClick={() => setStep(2)}
                    className="w-full"
                    disabled={!formData.name || !formData.subject || !formData.grade}
                  >
                    Next
                  </Button>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="customTheme">Custom Story Theme *</Label>
                    <Input
                      id="customTheme"
                      placeholder="e.g., Space Adventure, Mystery Detective, Time Travel"
                      value={formData.customTheme}
                      onChange={(event) => setFormData({ ...formData, customTheme: event.target.value })}
                    />
                    <p className="text-xs text-muted-foreground">
                      Enter a custom theme for your story generation (e.g., Space Adventure, Historical Fiction, Fantasy Quest)
                    </p>
                  </div>

                  <div className="space-y-3">
                    <Label>Design Style *</Label>
                    <div className="grid grid-cols-3 gap-3">
                      {styles.map((style) => (
                        <Card
                          key={style.id}
                          className={`cursor-pointer transition-all hover:shadow-md ${formData.style === style.id ? "border-primary border-2" : ""}`}
                          onClick={() => setFormData({ ...formData, style: style.id })}
                        >
                          <CardContent className="pt-6 text-center">
                            <div className="text-sm font-medium">{style.name}</div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                      Back
                    </Button>
                    <Button
                      onClick={handleSubmit}
                      className="flex-1"
                      disabled={!formData.customTheme || !formData.style}
                    >
                      Create Classroom
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default CreateClassroom;
