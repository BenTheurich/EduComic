import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { api } from "@/lib/api";

const StudentSignup = () => {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [interests, setInterests] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pendingClassroom, setPendingClassroom] = useState<{id: string, name: string} | null>(null);

  useEffect(() => {
    // Check if student is joining from a classroom invite
    const classroomId = sessionStorage.getItem('pendingClassroomId');
    const classroomName = sessionStorage.getItem('pendingClassroomName');
    
    if (classroomId && classroomName) {
      setPendingClassroom({ id: classroomId, name: classroomName });
    }
  }, []);

  const isFormValid = firstName.trim() && lastName.trim() && interests.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    setIsSubmitting(true);

    try {
      const fullName = `${firstName.trim()} ${lastName.trim()}`;
      toast.info("👤 Creating your account...");
      
      const response = await api.students.create(
        fullName,
        interests.trim(),
      );
      
      const studentId = response.student.id;

      // Enroll before avatar generation so the classroom design style is available.
      if (pendingClassroom) {
        toast.info(`🏫 Joining ${pendingClassroom.name}...`);
        await api.students.joinClassroom(studentId, pendingClassroom.id);
        
        // Clear session storage
        sessionStorage.removeItem('pendingClassroomId');
        sessionStorage.removeItem('pendingClassroomName');
        
        toast.success(`Joined ${pendingClassroom.name}!`);
      }

      try {
        toast.info("🎨 Generating your avatar...");
        await api.avatar.create(studentId);
        toast.success("Avatar generated!");
      } catch (avatarError) {
        console.error("Avatar generation failed:", avatarError);
        toast.error("Your account is ready, but avatar generation failed. You can retry from your profile.");
      }

      toast.success("✅ Account created successfully!");

      // Store student ID in localStorage for future logins
      localStorage.setItem('studentId', studentId);

      // Navigate to student dashboard
      navigate(`/student/dashboard/${studentId}`);
    } catch (error) {
      console.error("❌ Failed to create student:", error);
      
      // Show detailed error message
      const errorMessage = error instanceof Error ? error.message : "Failed to create account";
      toast.error(errorMessage);
      
      // Log full error for debugging
      console.error("Full error details:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="bg-background border-b">
        <div className="container mx-auto px-4 py-4">
          <Button variant="ghost" onClick={() => navigate("/")}>
            <ChevronLeft className="w-5 h-5 mr-2" />
            Back to Home
          </Button>
        </div>
      </header>

      <div className="container mx-auto px-4 py-12 max-w-2xl">
        <Card className="backdrop-blur-lg bg-card/70 border-2 border-border/50">
          <CardContent className="pt-8 pb-8 space-y-6">
            <div className="text-center">
              <div className="text-6xl mb-4">✨</div>
              <h1 className="text-3xl font-bold text-foreground mb-2">
                Create Your Account
              </h1>
              {pendingClassroom ? (
                <p className="text-muted-foreground">
                  Join <strong>{pendingClassroom.name}</strong> and set up your profile
                </p>
              ) : (
                <p className="text-muted-foreground">
                  Set up your profile to get started
                </p>
              )}
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Name Fields */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">
                    First Name <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="firstName"
                    type="text"
                    placeholder="Enter first name"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">
                    Last Name <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="lastName"
                    type="text"
                    placeholder="Enter last name"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Interests/Hobbies */}
              <div className="space-y-2">
                <Label htmlFor="interests">
                  Interests / Hobbies <span className="text-destructive">*</span>
                </Label>
                <Textarea
                  id="interests"
                  placeholder="Tell us about your interests and hobbies (e.g., Sports, Reading, Music, Science)"
                  value={interests}
                  onChange={(e) => setInterests(e.target.value)}
                  rows={3}
                  required
                />
                <p className="text-sm text-muted-foreground">
                  This helps personalize your character in stories
                </p>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={!isFormValid || isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating Account...
                  </>
                ) : (
                  `Create Account${pendingClassroom ? ` & Join ${pendingClassroom.name}` : ''}`
                )}
              </Button>

              {!isFormValid && (
                <p className="text-sm text-center text-muted-foreground">
                  Please fill in all required fields
                </p>
              )}
            </form>

            <div className="pt-4 border-t border-border/30 text-center">
              <p className="text-sm text-muted-foreground mb-3">
                Already have an account?
              </p>
              <Button onClick={() => navigate("/student/login")} variant="outline" size="sm">
                Sign In
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default StudentSignup;
