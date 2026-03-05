"use client";

import { motion } from "framer-motion";

const steps = [
  {
    number: "01",
    title: "Describe what you want to launch",
    desc: "Tell Klarnow AI about your product, audience, and goals.",
  },
  {
    number: "02",
    title: "Generate your campaign pack",
    desc: "Get pages, creatives, copy, and a clear action plan - instantly.",
  },
  {
    number: "03",
    title: "Publish, track, and improve",
    desc: "Go live, capture leads, and refine based on real results.",
  },
];

const HowItWorksSection = () => {
  return (
    <section className="py-32 px-6 relative">
      <div className="absolute inset-0 bg-gradient-radial pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-2xl mx-auto relative z-10"
      >
        <div className="text-center mb-20">
          <span className="inline-block text-xs font-semibold tracking-widest uppercase text-primary mb-4">
            Process
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            How it works
          </h2>
        </div>

        <div className="space-y-0">
          {steps.map((step, i) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{
                duration: 0.5,
                delay: i * 0.12,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="flex gap-7 relative group"
            >
              <div className="flex flex-col items-center">
                <div className="w-11 h-11 rounded-full border border-primary/30 bg-primary/10 flex items-center justify-center shrink-0 group-hover:border-primary/60 group-hover:bg-primary/20 transition-all duration-300">
                  <span className="text-xs font-bold text-primary">
                    {step.number}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className="w-px flex-1 bg-border/40 my-3" />
                )}
              </div>

              <div className="pb-14">
                <h3 className="text-base font-semibold text-foreground mb-2">
                  {step.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {step.desc}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
};

export default HowItWorksSection;
