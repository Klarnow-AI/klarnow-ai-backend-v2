"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  side?: "left" | "right" | "bottom";
}

export function Sheet({
  open,
  onOpenChange,
  children,
  side = "left",
}: SheetProps) {
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) onOpenChange(false);
    };
    if (open) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [open, onOpenChange]);

  const variants = {
    left: {
      initial: { x: "-100%" },
      animate: { x: 0 },
      exit: { x: "-100%" },
      transition: { type: "tween", duration: 0.25, ease: "easeInOut" },
    },
    right: {
      initial: { x: "100%" },
      animate: { x: 0 },
      exit: { x: "100%" },
      transition: { type: "tween", duration: 0.25, ease: "easeInOut" },
    },
    bottom: {
      initial: { y: "100%" },
      animate: { y: 0 },
      exit: { y: "100%" },
      transition: { type: "tween", duration: 0.25, ease: "easeInOut" },
    },
  };

  const v = variants[side];

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            onClick={() => onOpenChange(false)}
            aria-hidden
          />
          <motion.div
            initial={v.initial}
            animate={v.animate}
            exit={v.exit}
            transition={v.transition}
            className={cn(
              "fixed z-50 bg-card border-border shadow-2xl",
              side === "left" &&
                "left-0 top-0 bottom-0 w-full max-w-[min(320px,85vw)]",
              side === "right" &&
                "right-0 top-0 bottom-0 w-full max-w-[min(380px,95vw)]",
              side === "bottom" &&
                "left-0 right-0 bottom-0 max-h-[90vh] rounded-t-2xl border-t",
            )}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

interface SheetContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function SheetContent({
  className,
  children,
  ...props
}: SheetContentProps) {
  return (
    <div
      className={cn("flex flex-col h-full overflow-hidden", className)}
      {...props}
    >
      {children}
    </div>
  );
}

interface SheetHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function SheetHeader({
  className,
  children,
  ...props
}: SheetHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between shrink-0 p-4 border-b border-border",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
