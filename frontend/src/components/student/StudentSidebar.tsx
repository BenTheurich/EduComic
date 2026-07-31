import { Link } from "react-router-dom";
import { LayoutDashboard, Users, BookOpen, User, LogOut, ChevronDown, ChevronRight } from "lucide-react";
import { Sidebar, SidebarBody } from "@/components/ui/animated-sidebar";
import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import api from "@/lib/api";
import { cn } from "@/lib/utils";

interface StudentSidebarProps {
  studentId: string;
  open: boolean;
  setOpen: (open: boolean) => void;
}

type StudentClassroom = Awaited<ReturnType<typeof api.students.getClassrooms>>["classrooms"][number];

export function StudentSidebar({ studentId, open, setOpen }: StudentSidebarProps) {
  const [classrooms, setClassrooms] = useState<StudentClassroom[]>([]);
  const [classroomsExpanded, setClassroomsExpanded] = useState(false);

  useEffect(() => {
    const loadClassrooms = async () => {
      if (!studentId) return;

      try {
        const response = await api.students.getClassrooms(studentId);
        setClassrooms(response.classrooms || []);
      } catch {
        setClassrooms([]);
      }
    };

    loadClassrooms();
  }, [studentId]);

  return (
    <Sidebar open={open} setOpen={setOpen}>
      <SidebarBody className="justify-between gap-10">
        <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Logo open={open} />
          <div className="mt-8 space-y-1">
            {/* Dashboard */}
            <Link
              to={`/student/dashboard/${studentId}`}
              aria-label="Dashboard"
              className="flex min-h-11 items-center justify-start gap-2 group/sidebar py-2 px-2 rounded-md hover:bg-accent transition-colors"
            >
              <LayoutDashboard className="text-foreground h-5 w-5 flex-shrink-0" />
              <motion.span
                animate={{
                  display: open ? "inline-block" : "none",
                  opacity: open ? 1 : 0,
                }}
                className="text-foreground text-sm group-hover/sidebar:translate-x-1 transition duration-150 whitespace-pre inline-block !p-0 !m-0"
              >
                Dashboard
              </motion.span>
            </Link>

            {/* My Classrooms - Expandable */}
            <div>
              <button
                type="button"
                aria-label="My Classrooms"
                aria-expanded={classroomsExpanded}
                aria-controls="student-classrooms"
                onClick={() => setClassroomsExpanded(!classroomsExpanded)}
                className="flex min-h-11 w-full items-center justify-start gap-2 group/sidebar py-2 px-2 rounded-md hover:bg-accent transition-colors"
              >
                <Users className="text-foreground h-5 w-5 flex-shrink-0" />
                <motion.span
                  animate={{
                    display: open ? "inline-block" : "none",
                    opacity: open ? 1 : 0,
                  }}
                  className="text-foreground text-sm flex-1 text-left whitespace-pre inline-block !p-0 !m-0"
                >
                  My Classrooms
                </motion.span>
                {open && (
                  <motion.div
                    animate={{
                      rotate: classroomsExpanded ? 180 : 0,
                    }}
                    transition={{ duration: 0.2 }}
                  >
                    <ChevronDown className="h-4 w-4 text-foreground" />
                  </motion.div>
                )}
              </button>

              {/* Classroom List */}
              {open && classroomsExpanded && (
                <motion.div
                  id="student-classrooms"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="ml-7 mt-1 space-y-1 overflow-hidden"
                >
                  {classrooms.map((classroom) => (
                    <Link
                      key={classroom.id}
                      to={`/student/classroom/${classroom.id}/${studentId}`}
                      className="flex min-h-11 items-center gap-2 py-1.5 px-2 rounded-md hover:bg-accent/50 transition-colors text-sm text-muted-foreground hover:text-foreground"
                    >
                      <ChevronRight className="h-3 w-3 flex-shrink-0" />
                      <span className="truncate">{classroom.name}</span>
                    </Link>
                  ))}
                </motion.div>
              )}
            </div>

            {/* All Stories */}
            <Link
              to={`/student/stories/${studentId}`}
              aria-label="All Stories"
              className="flex min-h-11 items-center justify-start gap-2 group/sidebar py-2 px-2 rounded-md hover:bg-accent transition-colors"
            >
              <BookOpen className="text-foreground h-5 w-5 flex-shrink-0" />
              <motion.span
                animate={{
                  display: open ? "inline-block" : "none",
                  opacity: open ? 1 : 0,
                }}
                className="text-foreground text-sm group-hover/sidebar:translate-x-1 transition duration-150 whitespace-pre inline-block !p-0 !m-0"
              >
                All Stories
              </motion.span>
            </Link>

            {/* Profile */}
            <Link
              to={`/student/profile/${studentId}`}
              aria-label="Profile"
              className="flex min-h-11 items-center justify-start gap-2 group/sidebar py-2 px-2 rounded-md hover:bg-accent transition-colors"
            >
              <User className="text-foreground h-5 w-5 flex-shrink-0" />
              <motion.span
                animate={{
                  display: open ? "inline-block" : "none",
                  opacity: open ? 1 : 0,
                }}
                className="text-foreground text-sm group-hover/sidebar:translate-x-1 transition duration-150 whitespace-pre inline-block !p-0 !m-0"
              >
                Profile
              </motion.span>
            </Link>

            {/* Logout */}
            <Link
              to="/"
              aria-label="Logout"
              className="flex min-h-11 items-center justify-start gap-2 group/sidebar py-2 px-2 rounded-md hover:bg-accent transition-colors"
            >
              <LogOut className="text-foreground h-5 w-5 flex-shrink-0" />
              <motion.span
                animate={{
                  display: open ? "inline-block" : "none",
                  opacity: open ? 1 : 0,
                }}
                className="text-foreground text-sm group-hover/sidebar:translate-x-1 transition duration-150 whitespace-pre inline-block !p-0 !m-0"
              >
                Logout
              </motion.span>
            </Link>
          </div>
        </div>
      </SidebarBody>
    </Sidebar>
  );
}

const Logo = ({ open }: { open: boolean }) => {
  return (
    <Link
      to="/"
      aria-label="StoryClass Student home"
      className="font-normal flex min-h-11 space-x-2 items-center text-sm py-1 relative z-20"
    >
      <div className="h-5 w-6 bg-primary rounded-br-lg rounded-tr-sm rounded-tl-lg rounded-bl-sm flex-shrink-0" />
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: open ? 1 : 0 }}
        className="font-medium text-foreground whitespace-pre"
      >
        StoryClass Student
      </motion.span>
    </Link>
  );
};
