import { Link } from "react-router-dom";
import { BookOpen, Sparkles, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

const Landing = () => (
  <div className="min-h-screen bg-background">
    <header className="border-b">
      <div className="container mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="font-serif text-xl font-semibold" aria-label="EduComic home">EduComic</Link>
        <span className="font-mono text-xs font-bold text-muted-foreground">LOCAL · BYOK</span>
      </div>
    </header>

    <main className="container mx-auto max-w-6xl px-4 py-12 sm:py-20">
      <section className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <p className="mb-4 font-mono text-xs font-bold tracking-wide text-primary">THE AUTHORED COMIC WORKSHOP</p>
          <h1 className="max-w-3xl font-serif text-4xl font-semibold leading-[1.08] tracking-tight text-foreground sm:text-6xl">
            Turn today’s lesson into a comic students can step inside.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
            Shape a lesson, choose a story direction, and create a classroom graphic novel with students as the cast.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="w-full sm:w-auto">
              <Link to="/teacher/dashboard">Get Started as Teacher</Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="w-full sm:w-auto">
              <Link to="/student/select">Choose Student Profile</Link>
            </Button>
          </div>
          <p className="mt-5 font-mono text-xs text-muted-foreground">Local project data · bring your own API keys</p>
        </div>

        <div className="rounded-lg border bg-card p-5 sm:p-7" aria-label="Lesson to comic workflow">
          <div className="mb-5 flex items-center justify-between border-b pb-4">
            <span className="font-mono text-xs font-bold text-muted-foreground">STORY IN PRODUCTION</span>
            <span className="h-3 w-3 rounded-full bg-story-spark ring-1 ring-foreground/20" aria-hidden="true" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="border p-5">
              <BookOpen className="mb-6 h-7 w-7 text-primary" aria-hidden="true" />
              <p className="font-mono text-xs text-muted-foreground">01 · LESSON</p>
              <p className="mt-2 font-semibold">Ground the story in what was taught.</p>
            </div>
            <div className="border p-5">
              <Users className="mb-6 h-7 w-7 text-primary" aria-hidden="true" />
              <p className="font-mono text-xs text-muted-foreground">02 · CAST</p>
              <p className="mt-2 font-semibold">Bring the classroom into the adventure.</p>
            </div>
            <div className="border-2 border-foreground/15 bg-story-spark/20 p-5 sm:col-span-2">
              <Sparkles className="mb-6 h-7 w-7 text-primary" aria-hidden="true" />
              <p className="font-mono text-xs text-muted-foreground">03 · COMIC</p>
              <p className="mt-2 font-serif text-2xl font-semibold">Review, refine, read, and export the finished story.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-16 grid gap-0 border-y sm:grid-cols-3" aria-label="How EduComic works">
        {[
          ["01", "Brief the lesson", "Write a prompt or ground it in selected PDF materials."],
          ["02", "Choose the direction", "Compare three complete story ideas and their previews."],
          ["03", "Make the comic", "Watch durable panels arrive, then review and export."],
        ].map(([number, title, description]) => (
          <div key={number} className="p-6 sm:border-r sm:last:border-r-0">
            <p className="font-mono text-xs font-bold text-primary">{number}</p>
            <h2 className="mt-3 text-lg font-semibold">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
          </div>
        ))}
      </section>
    </main>
  </div>
);

export default Landing;
