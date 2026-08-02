import { ArrowRight, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const Landing = () => (
  <div className="min-h-screen bg-background">
    <header className="border-b bg-card">
      <nav
        aria-label="Primary navigation"
        className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-2 sm:px-10"
      >
        <Link
          to="/"
          className="font-serif text-2xl font-semibold tracking-[-0.02em] text-foreground"
          aria-label="EduComic home"
        >
          EduComic
        </Link>

        <div className="flex min-h-11 items-center text-sm font-semibold text-primary">
          <Link
            to="/teacher/dashboard"
            aria-label="Teacher workspace"
            className="flex min-h-11 items-center border-r px-3 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:px-5"
          >
            <span className="sm:hidden">Teacher</span>
            <span className="hidden sm:inline">I'm a Teacher</span>
          </Link>
          <Link
            to="/student/select"
            aria-label="Student profiles"
            className="flex min-h-11 items-center px-3 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:px-5"
          >
            <span className="sm:hidden">Student</span>
            <span className="hidden sm:inline">I'm a Student</span>
          </Link>
        </div>
      </nav>
    </header>

    <main>
      <section className="overflow-hidden border-b text-primary-foreground">
        <div className="relative bg-[radial-gradient(circle_at_34%_28%,hsl(200_98%_40%),hsl(var(--primary))_68%)]">
          <div className="relative mx-auto max-w-[1500px] px-4 pb-8 pt-10 sm:px-10 sm:pt-14 lg:h-[572px] lg:px-12 lg:py-0">
            <div className="relative z-10 max-w-xl lg:absolute lg:left-12 lg:top-[82px] lg:w-[39%]">
              <h1 className="font-serif text-4xl font-semibold leading-[1.04] tracking-[-0.03em] sm:text-5xl lg:text-[3.85rem]">
                <span className="block lg:whitespace-nowrap">Turn a lesson</span>
                <span className="block lg:whitespace-nowrap">into a comic</span>
                <span className="block lg:whitespace-nowrap">starring your class.</span>
              </h1>
              <p className="mt-6 max-w-lg text-lg leading-7 text-primary-foreground/90">
                <span className="block">Students become the heroes of their learning.</span>
                <span className="block">You bring the lesson. We turn it into a comic.</span>
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button
                  asChild
                  size="lg"
                  className="h-14 w-full bg-card px-6 text-primary hover:bg-card/90 sm:w-auto"
                >
                  <Link to="/teacher/dashboard">
                    Get Started
                    <ArrowRight aria-hidden="true" />
                  </Link>
                </Button>
                <a
                  href="#how-it-works"
                  className="inline-flex h-14 w-full items-center justify-center rounded-md border border-primary-foreground/80 px-7 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-foreground/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-primary sm:w-auto"
                >
                  See How It Works
                </a>
              </div>
            </div>

            <div className="relative mt-10 h-[390px] w-full lg:absolute lg:inset-0 lg:mt-0 lg:h-full">
              <figure className="absolute right-[-20%] top-[2%] z-50 w-[108%] -rotate-3 border-[8px] border-card bg-card shadow-[0_30px_48px_-20px_hsl(222_47%_11%/0.78)] sm:right-[-7%] sm:w-[92%] sm:border-[12px] lg:right-[-5%] lg:top-[5.5%] lg:w-[55%] lg:max-w-[790px] lg:-rotate-[4deg]">
                <img
                  src="/demo/condensation-jar.png"
                  alt="Maya and her fictional classmates investigate condensation"
                  className="aspect-[4/3] w-full border-2 border-foreground object-cover 2xl:aspect-[25/16]"
                />
              </figure>

              <figure className="absolute bottom-0 left-0 z-[60] w-[31%] rotate-6 border-[7px] border-card bg-card shadow-[0_22px_38px_-18px_hsl(222_47%_11%/0.82)] sm:border-[9px] lg:bottom-[1.5%] lg:left-[39.5%] lg:w-[15%] lg:max-w-[215px] lg:rotate-[5deg]">
                <img
                  src="/demo/maya-fictional-portrait.png"
                  alt="Fictional portrait of Maya Rivers"
                  className="aspect-[3/4] w-full object-cover"
                />
              </figure>

              <figure className="absolute bottom-[3%] left-[24%] z-[70] size-[20%] overflow-hidden rounded-full border-[6px] border-card bg-card shadow-[0_16px_30px_-13px_hsl(222_47%_11%/0.9)] sm:border-[8px] lg:bottom-[7%] lg:left-[51.7%] lg:size-[8.5vw] lg:max-h-[118px] lg:max-w-[118px]">
                <img
                  src="/demo/maya-avatar-bfl.jpg"
                  alt="Comic avatar generated from Maya's fictional portrait"
                  className="absolute left-1/2 top-[-6%] w-[220%] max-w-none -translate-x-1/2"
                />
              </figure>

              <svg
                viewBox="0 0 150 85"
                className="absolute bottom-[1%] left-[2%] z-[65] w-[35%] overflow-visible text-primary-foreground lg:bottom-[6%] lg:left-[36.3%] lg:w-[9%]"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M8 12C17 55 42 72 80 71C102 70 118 61 130 49"
                  stroke="currentColor"
                  strokeWidth="5.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M115 52L133 48L128 66"
                  stroke="currentColor"
                  strokeWidth="5.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>
        </div>

        <ol className="relative z-40 grid h-20 grid-cols-3 divide-x border-t bg-card text-foreground">
          {["Photo", "Character", "Comic"].map((label, index) => (
            <li key={label} className="relative overflow-visible">
              <span className="absolute left-[30%] top-1/2 -translate-y-1/2 font-mono text-xs font-bold uppercase tracking-[0.12em] sm:text-sm">
                {label}
              </span>
              {index < 2 && (
                <svg
                  viewBox="0 0 220 14"
                  className="absolute left-[58%] top-1/2 hidden w-[63%] -translate-y-1/2 overflow-visible text-foreground/55 sm:block"
                  aria-hidden="true"
                >
                  <path d="M1 7H211" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 5" />
                  <path d="M211 3L219 7L211 11Z" fill="currentColor" />
                </svg>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section id="how-it-works" className="scroll-mt-4 bg-card py-16 sm:py-20">
        <div className="container mx-auto max-w-7xl px-4 sm:px-6">
          <div className="max-w-2xl">
            <h2 className="font-serif text-3xl font-semibold leading-tight tracking-[-0.02em] sm:text-4xl">
              From lesson material to finished story.
            </h2>
            <p className="mt-4 text-lg leading-8 text-muted-foreground">
              The lesson sets the science. A fictional classroom becomes the cast. The comic brings both together.
            </p>
          </div>

          <ol className="mt-10 border-y lg:grid lg:grid-cols-3 lg:divide-x">
            <li className="py-8 lg:pr-8">
              <p className="font-mono text-xs font-bold uppercase tracking-[0.08em] text-primary">Lesson material</p>
              <div className="mt-5 border bg-background p-5 shadow-sm">
                <div className="flex items-center gap-3 border-b pb-4">
                  <FileText className="size-6 text-primary" aria-hidden="true" />
                  <div>
                    <p className="font-semibold">How clouds make rain</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">Grade 5 science</p>
                  </div>
                </div>
                <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                  <li>Water vapor rises and cools.</li>
                  <li>Cooling forms liquid droplets.</li>
                  <li>Droplets gather and fall as rain.</li>
                </ul>
              </div>
            </li>

            <li className="border-t py-8 lg:border-t-0 lg:px-8">
              <p className="font-mono text-xs font-bold uppercase tracking-[0.08em] text-primary">Fictional student</p>
              <figure className="mt-5 grid grid-cols-[1fr_0.78fr] overflow-hidden border bg-background shadow-sm">
                <img
                  src="/demo/maya-fictional-portrait.png"
                  alt=""
                  loading="lazy"
                  className="aspect-square h-full w-full object-cover"
                />
                <img
                  src="/demo/maya-avatar-bfl.jpg"
                  alt=""
                  loading="lazy"
                  className="aspect-square h-full w-full border-l object-cover"
                />
                <figcaption className="col-span-2 border-t px-4 py-3 text-sm text-muted-foreground">
                  Maya Rivers · fictional classroom sample
                </figcaption>
              </figure>
            </li>

            <li className="border-t py-8 lg:border-t-0 lg:pl-8">
              <p className="font-mono text-xs font-bold uppercase tracking-[0.08em] text-primary">Finished story</p>
              <figure className="mt-5 overflow-hidden border-2 border-foreground bg-background shadow-sm">
                <img
                  src="/demo/condensation-jar.png"
                  alt="Condensation experiment panel from the fictional story"
                  loading="lazy"
                  className="aspect-[4/3] w-full object-cover"
                />
                <figcaption className="border-t-2 border-foreground px-4 py-3 text-sm leading-6 text-muted-foreground">
                  Water vapor cools and condenses into droplets—the same process that helps form clouds and rain.
                </figcaption>
              </figure>
            </li>
          </ol>
        </div>
      </section>
    </main>
  </div>
);

export default Landing;
