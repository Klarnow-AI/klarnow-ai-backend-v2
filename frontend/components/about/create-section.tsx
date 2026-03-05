"use client";

import { motion } from "framer-motion";
import { BarChart3, FileText, Image, Layers } from "@/components/icons";

const items = [
  {
    icon: FileText,
    label: "Landing Pages",
    desc: "High-converting pages built from your campaign brief",
  },
  {
    icon: Image,
    label: "Posters",
    desc: "On-brand creative assets ready to share",
  },
  {
    icon: Layers,
    label: "Ad Factory",
    desc: "Multi-format ad variations generated instantly",
  },
  {
    icon: BarChart3,
    label: "Tracker",
    desc: "Monitor performance and iterate in real time",
  },
];

const CreateSection = () => {
  return (
    <section className="py-32 px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-4xl mx-auto"
      >
        <div className="text-center mb-16">
          <span className="inline-block text-xs font-semibold tracking-widest uppercase text-primary mb-4">
            Capabilities
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            What you can create
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {items.map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                duration: 0.5,
                delay: i * 0.08,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="group relative p-8 rounded-2xl bg-card border border-border/50 hover:border-primary/25 hover:shadow-glow transition-all duration-500 cursor-default overflow-hidden"
            >
              <div className="absolute inset-0 bg-primary/[0.02] opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl" />

              <div className="relative z-10">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6 group-hover:bg-primary/15 transition-colors duration-300">
                  <item.icon size={22} className="text-primary" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  {item.label}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {item.desc}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
};

export default CreateSection;
