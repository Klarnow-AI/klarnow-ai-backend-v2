"use client";

import { motion } from "framer-motion";

type ExplainerSectionProps = {
  onGetStarted: () => void;
};

const ExplainerSection = ({ onGetStarted }: ExplainerSectionProps) => {
  return (
    <section id="about" className="relative pt-40 pb-20 px-6">
      <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-2xl mx-auto text-center relative z-10"
      >
        <span className="inline-block text-xs font-semibold tracking-widest uppercase text-primary mb-5">
          Our approach
        </span>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-foreground mb-6 leading-[1.1]">
          From idea to action, in one guided sprint.
        </h1>
        <p className="text-base sm:text-lg text-muted-foreground leading-relaxed max-w-xl mx-auto mb-14">
          Klarnow AI helps businesses turn loose ideas into clearer offers,
          campaign assets, conversion pages, and next steps that move people to
          act.
        </p>

        <div className="flex items-center justify-center gap-4">
          <button
            type="button"
            onClick={onGetStarted}
            className="px-8 py-3.5 rounded-full bg-primary text-primary-foreground text-sm font-semibold shadow-glow hover:shadow-glow-strong hover:scale-[1.02] transition-all duration-300"
          >
            Start Building Your Brand
          </button>
        </div>
      </motion.div>
    </section>
  );
};

export default ExplainerSection;
