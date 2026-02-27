"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useDynamicPopover } from "@/hooks/use-dynamic-popover";
import { cn } from "@/lib/utils";
import type { Placement } from "@floating-ui/react-dom";

export interface DynamicPopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trigger: React.ReactNode;
  children: React.ReactNode;
  placement?: Placement;
  contentClassName?: string;
}

export function DynamicPopover({
  open,
  onOpenChange,
  trigger,
  children,
  placement = "bottom-start",
  contentClassName,
}: DynamicPopoverProps) {
  const { refs, floatingStyles, isPositioned } = useDynamicPopover({
    open,
    placement,
  });

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      const ref = refs.reference.current;
      if (
        (ref instanceof Element && ref.contains(target)) ||
        refs.floating.current?.contains(target)
      )
        return;
      onOpenChange(false);
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open, onOpenChange, refs.reference, refs.floating]);

  useEffect(() => {
    if (!open) return;
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") onOpenChange(false);
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [open, onOpenChange]);

  const triggerWithRef = (
    <div ref={refs.setReference} onClick={() => onOpenChange(!open)}>
      {trigger}
    </div>
  );

  const floatingContent =
    typeof document !== "undefined" &&
    createPortal(
      <AnimatePresence>
        {open && (
          <div
            ref={refs.setFloating}
            style={{
              ...floatingStyles,
              visibility: isPositioned ? "visible" : "hidden",
            }}
          >
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: isPositioned ? 1 : 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className={cn(
                "z-50 rounded-xl border border-border bg-card shadow shadow-black/10",
                contentClassName,
              )}
            >
              {children}
            </motion.div>
          </div>
        )}
      </AnimatePresence>,
      document.body,
    );

  return (
    <>
      {triggerWithRef}
      {floatingContent}
    </>
  );
}
