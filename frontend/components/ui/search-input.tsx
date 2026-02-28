"use client";

import { forwardRef } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface SearchInputProps extends Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "size"
> {
  /** Content rendered before the input (e.g. icon button) */
  leftAdornment?: React.ReactNode;
  /** Content rendered after the input (e.g. chips, icon button) */
  rightAdornment?: React.ReactNode;
  /** Optional wrapper class (e.g. for motion) */
  wrapperClassName?: string;
  /** Whether to use subtle focus scale effect */
  focusScale?: boolean;
  /** "default" = bordered card style, "minimal" = no background/border */
  variant?: "default" | "minimal";
}

const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  (
    {
      className,
      leftAdornment,
      rightAdornment,
      wrapperClassName,
      focusScale = true,
      variant = "default",
      ...props
    },
    ref,
  ) => {
    const Wrapper = focusScale && variant === "default" ? motion.div : "div";
    const wrapperProps =
      focusScale && variant === "default"
        ? { whileFocus: { scale: 1.01 } as const }
        : {};

    const isMinimal = variant === "minimal";

    return (
      <Wrapper
        className={cn(
          "relative flex items-center gap-3 w-full px-5 py-4 transition-all",
          isMinimal
            ? "border-0 border-b border-border/50 bg-transparent rounded-none focus-within:border-foreground/40 focus-within:scale-100"
            : "rounded-full border-0 bg-border/40 focus-within:bg-border/60 focus-within:ring-1 focus-within:ring-foreground/20 focus-within:scale-[1.02]",
          wrapperClassName,
        )}
        {...wrapperProps}
      >
        {leftAdornment && (
          <div className="flex items-center shrink-0">{leftAdornment}</div>
        )}
        <input
          ref={ref}
          type="text"
          className={cn(
            "flex-1 min-w-0 bg-transparent text-foreground placeholder:text-muted-foreground text-base outline-none",
            className,
          )}
          {...props}
        />
        {rightAdornment && (
          <div className="flex items-center gap-2 shrink-0">
            {rightAdornment}
          </div>
        )}
      </Wrapper>
    );
  },
);
SearchInput.displayName = "SearchInput";

export { SearchInput };
