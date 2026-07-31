import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { User, Mail, Heart } from "lucide-react";
import api from "@/lib/api";

type Student = Awaited<ReturnType<typeof api.students.getById>>["student"];

const StudentProfile = () => {
    const { studentId } = useParams();
    const [student, setStudent] = useState<Student | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [avatarError, setAvatarError] = useState<string | null>(null);
    const [generatingAvatar, setGeneratingAvatar] = useState(false);

    useEffect(() => {
        if (!studentId) return;
        const loadStudentData = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.students.getById(studentId);
            setStudent(response.student);
        } catch {
            setError("Failed to load student profile");
        } finally {
            setLoading(false);
        }
        };
        loadStudentData();
    }, [studentId]);

    const getInitials = (name: string) =>
        name.split(' ').map(n => n[0]).join('').toUpperCase();

    const retryAvatar = async () => {
        if (!studentId) return;
        setGeneratingAvatar(true);
        setAvatarError(null);
        try {
            const response = await api.avatar.create(studentId);
            setStudent(response.student);
        } catch {
            setAvatarError("Avatar generation failed. Please try again.");
        } finally {
            setGeneratingAvatar(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <p className="text-muted-foreground">Loading...</p>
            </div>
        );
    }

    if (error || !student) {
        return (
            <div className="flex items-center justify-center h-screen">
                <p className="text-destructive">{error || "Student not found"}</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-muted/20">
            <div className="container mx-auto px-4 py-8 max-w-4xl">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <h1 className="text-4xl font-bold text-foreground mb-8">My Profile</h1>

                    {/* Profile Card */}
                    <Card className="backdrop-blur-lg bg-card/70 border-2 border-border/50 mb-6">
                        <CardContent className="pt-8 pb-8">
                            <div className="flex flex-col md:flex-row gap-8 items-start">
                                {/* Avatar Section */}
                                <div className="flex flex-col items-center space-y-4">
                                    <Avatar className="w-32 h-32 border-4 border-primary/20">
                                        <AvatarImage src={student.avatar_url || undefined} />
                                        <AvatarFallback className="bg-primary/20 text-4xl">
                                            {getInitials(student.name)}
                                        </AvatarFallback>
                                    </Avatar>
                                    {!student.avatar_url && (
                                        <Button variant="outline" size="sm" onClick={retryAvatar} disabled={generatingAvatar}>
                                            {generatingAvatar ? "Generating Avatar..." : "Try Avatar Again"}
                                        </Button>
                                    )}
                                    {avatarError && <p role="alert" className="text-sm text-destructive">{avatarError}</p>}
                                </div>

                                {/* Account Details */}
                                <div className="flex-1 space-y-6">
                                    <div>
                                        <h2 className="text-2xl font-bold text-foreground mb-1">{student.name}</h2>
                                        <Badge variant="outline" className="mt-2">Student</Badge>
                                    </div>

                                    <div className="space-y-4">
                                        {/* Student ID */}
                                        <div className="flex items-start gap-3 p-4 bg-muted/50 rounded-lg">
                                            <User className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                                            <div className="flex-1">
                                                <p className="text-sm font-medium text-muted-foreground">Student ID</p>
                                                <p className="text-foreground font-mono text-sm">{student.id}</p>
                                            </div>
                                        </div>

                                        {/* Interests */}
                                        <div className="flex items-start gap-3 p-4 bg-muted/50 rounded-lg">
                                            <Heart className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                                            <div className="flex-1">
                                                <p className="text-sm font-medium text-muted-foreground">Interests & Hobbies</p>
                                                <p className="text-foreground">{student.interests}</p>
                                            </div>
                                        </div>

                                        {/* Member Since */}
                                        <div className="flex items-start gap-3 p-4 bg-muted/50 rounded-lg">
                                            <Mail className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                                            <div className="flex-1">
                                                <p className="text-sm font-medium text-muted-foreground">Member Since</p>
                                                <p className="text-foreground">
                                                    {new Date(student.created_at).toLocaleDateString('en-US', {
                                                        year: 'numeric',
                                                        month: 'long',
                                                        day: 'numeric'
                                                    })}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                </motion.div>
            </div>
        </div>
    );
};

export default StudentProfile;
