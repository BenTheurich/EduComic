import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const Landing = () => (
  <div className="flex min-h-screen flex-col bg-background">
    <header className="border-b">
      <div className="container mx-auto flex max-w-7xl items-center px-4 py-5 sm:px-6">
        <Link to="/" className="font-serif text-2xl font-semibold" aria-label="EduComic home">
          EduComic
        </Link>
      </div>
    </header>

    <main className="flex flex-1 items-center">
      <section className="container mx-auto grid max-w-7xl items-center gap-10 px-4 py-10 sm:px-6 sm:py-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
        <div className="max-w-xl">
          <h1 className="text-balance text-4xl font-bold leading-[1.05] tracking-[-0.035em] text-foreground sm:text-5xl lg:text-6xl">
            Turn a lesson into a comic starring your class.
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-muted-foreground">
            Create illustrated stories grounded in what you teach, with students at the heart of the adventure.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="w-full sm:w-auto">
              <Link to="/teacher/dashboard">Get Started as Teacher</Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="w-full sm:w-auto">
              <Link to="/student/select">Choose Student Profile</Link>
            </Button>
          </div>
        </div>

        <figure className="mx-auto w-full max-w-2xl overflow-hidden rounded-lg border-2 border-foreground bg-card">
          <img
            src="/demo/weather-lab-raindrop-reveal.png"
            alt="Fictional student investigates rainfall outside the Weather Lab"
            className="aspect-square w-full object-cover"
          />
          <figcaption className="flex flex-col gap-1 border-t-2 border-foreground bg-primary px-4 py-3 text-primary-foreground sm:flex-row sm:items-center sm:justify-between">
            <span className="font-semibold">The Great Raindrop Reveal</span>
            <span className="text-sm">Fictional classroom sample</span>
          </figcaption>
        </figure>
      </section>
    </main>
  </div>
);

export default Landing;
