"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sun, Moon, Monitor } from "@/components/icons";
import { useTheme, type Theme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";

type ThemeOption = { value: Theme; icon: typeof Sun; label: string };

const options: ThemeOption[] = [
  { value: "light", icon: Sun, label: "Light" },
  { value: "dark", icon: Moon, label: "Dark" },
  { value: "system", icon: Monitor, label: "System" },
];

export function ThemeSettingsPopover({
  trigger,
  open,
  onOpenChange,
}: {
  trigger: React.ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { theme, setTheme } = useTheme();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        onOpenChange(false);
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open, onOpenChange]);

  return (
    <div className="relative" ref={ref}>
      <div onClick={() => onOpenChange(!open)}>{trigger}</div>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 z-50 w-56 rounded-xl border border-border bg-card p-3 shadow shadow-black/10"
          >
            {/* Theme row */}
            <div className="flex items-center gap-1.5 mb-3">
              {options.map((opt) => {
                const Icon = opt.icon;
                const isSelected = theme === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setTheme(opt.value)}
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-lg border transition-colors",
                      isSelected
                        ? "bg-muted border-border text-foreground"
                        : "border-transparent text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
                    )}
                    title={opt.label}
                    aria-label={opt.label}
                  >
                    <Icon className="h-4 w-4" />
                  </button>
                );
              })}
            </div>
            {/* Language */}
            <div className="pt-2 border-t border-border">
              <p className="text-sm font-medium text-foreground">Language</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Display language (coming soon)
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
