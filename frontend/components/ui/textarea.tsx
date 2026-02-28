"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-xl border-0 bg-border/40 px-4 py-3 text-base sm:text-sm text-foreground placeholder:text-muted-foreground transition-all",
          "focus:outline-none focus:scale-[1.02] focus:bg-border/60 focus:ring-1 focus:ring-foreground/20",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "resize-y",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

export { Textarea };
