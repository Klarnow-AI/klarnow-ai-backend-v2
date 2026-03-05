"use client";

import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

type FooterCTAProps = {
  onGetStarted: () => void;
};

const FooterCTA = ({ onGetStarted }: FooterCTAProps) => {
  return (
    <section className="py-36 px-6 relative">
      <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-lg mx-auto text-center relative z-10"
      >
        <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground mb-5">
          Ready to launch something real?
        </h2>
        <p className="text-base sm:text-lg text-muted-foreground mb-12">
          Start your first campaign sprint in minutes.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Button
            type="button"
            size="lg"
            className="rounded-full px-9 h-12 text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow hover:shadow-glow-strong transition-all duration-300"
            onClick={onGetStarted}
          >
            Get Started
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="lg"
            className="rounded-full px-8 h-12 text-sm text-muted-foreground hover:text-foreground border border-border hover:border-primary/30 transition-all duration-300"
            onClick={() => {
              document.getElementById("about")?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              });
            }}
          >
            Learn More
          </Button>
        </div>
      </motion.div>

      <div className="max-w-6xl mx-auto mt-32 pt-8 border-t border-border/30 flex flex-col sm:flex-row items-center justify-between gap-4 relative z-10">
        <span className="text-xs text-text-tertiary">(c) 2026 Klarnow AI</span>
        <div className="flex items-center gap-6">
          <a
            href="#"
            className="text-xs text-text-tertiary hover:text-muted-foreground transition-colors duration-200"
          >
            Privacy
          </a>
          <a
            href="#"
            className="text-xs text-text-tertiary hover:text-muted-foreground transition-colors duration-200"
          >
            Terms
          </a>
        </div>
      </div>
    </section>
  );
};

export default FooterCTA;
