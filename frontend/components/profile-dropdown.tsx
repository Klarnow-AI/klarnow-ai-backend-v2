"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  LogOut,
  HelpCircle,
  Sun,
  Moon,
  Monitor,
} from "@/components/icons";
import { useAuth } from "@/contexts/auth-context";
import { useTheme, type Theme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";

export function ProfileDropdown({
  open,
  onOpenChange,
  children,
  className,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children?: React.ReactNode;
  className?: string;
}) {
  const { logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const ref = useRef<HTMLDivElement>(null);

  const themeOptions: { value: Theme; icon: typeof Sun; label: string }[] = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "system", icon: Monitor, label: "System" },
  ];

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
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        className={cn(className, "transition-all hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black focus-visible:outline-none focus-visible:ring-0 hover:scale-105")}
        aria-label="Profile menu"
        aria-expanded={open}
      >
        {children}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 z-50 w-52 rounded-xl border border-border bg-card py-1 shadow shadow-black/10"
          >
            <div className="flex items-center gap-1.5 px-3 py-2 border-b border-border">
              {themeOptions.map((opt) => {
                const Icon = opt.icon;
                const isSelected = theme === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setTheme(opt.value)}
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-lg border transition-all focus-visible:outline-none focus-visible:ring-0",
                      isSelected
                        ? "font-bold text-primary scale-105 border-transparent"
                        : "border-transparent text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black hover:scale-105"
                    )}
                    title={opt.label}
                    aria-label={opt.label}
                  >
                    <Icon className="h-4 w-4" />
                  </button>
                );
              })}
            </div>
            <Link
              href="/settings"
              className="flex items-center gap-3 px-3 py-2.5 text-sm text-foreground hover:bg-white/5 hover:scale-[1.02] transition-all focus-visible:outline-none focus-visible:ring-0"
              onClick={() => onOpenChange(false)}
            >
              <User className="h-4 w-4 shrink-0 text-muted-foreground" />
              View account
            </Link>
            <Link
              href="/help"
              className="flex items-center gap-3 px-3 py-2.5 text-sm text-foreground hover:bg-white/5 hover:scale-[1.02] transition-all focus-visible:outline-none focus-visible:ring-0"
              onClick={() => onOpenChange(false)}
            >
              <HelpCircle className="h-4 w-4 shrink-0 text-muted-foreground" />
              Help
            </Link>
            <button
              type="button"
              onClick={() => {
                logout();
                onOpenChange(false);
              }}
              className="flex w-full items-center gap-3 px-3 py-2.5 text-sm text-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all text-left focus-visible:outline-none focus-visible:ring-0 hover:scale-[1.02]"
            >
              <LogOut className="h-4 w-4 shrink-0 text-muted-foreground" />
              Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
