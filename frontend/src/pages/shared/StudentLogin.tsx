import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, User, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { api } from "@/lib/api";

interface Student {
    id: string;
    name: string;
    interests: string;
    avatar_url: string | null;
    created_at: string;
}

const StudentProfilePicker = () => {
    const navigate = useNavigate();
    const [students, setStudents] = useState<Student[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);

    useEffect(() => {
        fetchAllStudents();
    }, []);

    const fetchAllStudents = async () => {
        setIsLoading(true);
        setLoadError(null);
        try {
            const response = await api.students.getAll();
            setStudents(response.students);
        } catch {
            setLoadError("Failed to load students. Please try again.");
            toast.error("Failed to load students. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleStudentClick = (studentId: string) => {
        // Remember the selected local preview profile on this device.
        localStorage.setItem('studentId', studentId);
        navigate(`/student/dashboard/${studentId}`);
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
                            <div className="text-6xl mb-4">🎓</div>
                            <h1 className="text-3xl font-bold text-foreground mb-2">Choose a Student Profile</h1>
                            <p className="text-muted-foreground">
                                This selects a local preview only. It does not authenticate anyone.
                            </p>
                        </div>

                        <div className="space-y-3">
                            {isLoading ? (
                                <div className="flex flex-col items-center justify-center py-12">
                                    <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
                                    <p className="text-muted-foreground">Loading students...</p>
                                </div>
                            ) : loadError ? (
                                <div className="flex flex-col items-center py-12 text-center">
                                    <p role="alert" className="mb-4 text-muted-foreground">{loadError}</p>
                                    <Button variant="outline" onClick={fetchAllStudents}>Retry</Button>
                                </div>
                            ) : students.length === 0 ? (
                                <div className="text-center py-12">
                                    <p className="text-muted-foreground mb-4">No student profiles found</p>
                                    <p className="text-sm text-muted-foreground">
                                        Create a local profile to get started
                                    </p>
                                </div>
                            ) : (
                                students.map((student) => (
                                    <button
                                        key={student.id}
                                        type="button"
                                        aria-label={`Continue as ${student.name}`}
                                        className="w-full rounded-lg border-2 bg-card text-left text-card-foreground shadow-sm transition-all hover:bg-accent hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                        onClick={() => handleStudentClick(student.id)}
                                    >
                                        <CardContent className="pt-4 pb-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    {student.avatar_url ? (
                                                        <img
                                                            src={student.avatar_url}
                                                            alt={student.name}
                                                            className="w-12 h-12 rounded-full object-cover"
                                                        />
                                                    ) : (
                                                        <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
                                                            <User className="w-6 h-6 text-primary" />
                                                        </div>
                                                    )}
                                                    <div>
                                                        <h3 className="font-semibold text-foreground">{student.name}</h3>
                                                        <p className="text-sm text-muted-foreground">{student.interests}</p>
                                                    </div>
                                                </div>
                                                <Badge variant="outline">Student</Badge>
                                            </div>
                                        </CardContent>
                                    </button>
                                ))
                            )}
                        </div>

                        <div className="pt-4 border-t border-border/30 text-center">
                            <p className="text-sm text-muted-foreground mb-3">
                                New to the platform?
                            </p>
                            <Button onClick={() => navigate("/student/signup")} variant="outline" size="sm">
                                Create Student Profile
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default StudentProfilePicker;
