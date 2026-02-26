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
}

const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  (
    {
      className,
      leftAdornment,
      rightAdornment,
      wrapperClassName,
      focusScale = true,
      ...props
    },
    ref,
  ) => {
    const Wrapper = focusScale ? motion.div : "div";
    const wrapperProps = focusScale
      ? { whileFocus: { scale: 1.01 } as const }
      : {};

    return (
      <Wrapper
        className={cn(
          "relative flex items-center gap-3 w-full rounded-full border border-border bg-card px-5 py-4",
          "focus-within:border-foreground/30 focus-within:scale-[1.02] transition-all",
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
