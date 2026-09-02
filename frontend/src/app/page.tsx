import { Navbar } from "@/features/landing/navbar";
import { Hero } from "@/features/landing/hero";
import { Overview } from "@/features/landing/overview";
import { HowItWorks } from "@/features/landing/how-it-works";
import { About } from "@/features/landing/about";
import { Footer } from "@/features/landing/footer";
import { CursorTrail } from "@/features/landing/cursor-trail";
import "@/features/landing/landing.css";

export default function Home() {
  return (
    <main className="landing-root relative">
      <CursorTrail />
      <Navbar />
      <Hero />
      <Overview />
      <HowItWorks />
      <About />
      <Footer />
    </main>
  );
}
