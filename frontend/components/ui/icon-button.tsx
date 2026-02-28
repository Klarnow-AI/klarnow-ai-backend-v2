"use client";

import { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const iconButtonVariants = cva(
  "inline-flex items-center justify-center rounded-full shrink-0 transition-all focus-visible:outline-none focus-visible:scale-105 hover:scale-105 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        ghost:
          "text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
        solid:
          "bg-foreground text-background hover:bg-foreground/90 hover:text-background",
        outline:
          "border-0 bg-border/40 text-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
      },
      size: {
        sm: "h-9 w-9 [&>svg]:h-4 [&>svg]:w-4",
        md: "h-10 w-10 [&>svg]:h-5 [&>svg]:w-5",
        lg: "h-11 w-11 [&>svg]:h-5 [&>svg]:w-5",
      },
    },
    defaultVariants: {
      variant: "ghost",
      size: "md",
    },
  },
);

export interface IconButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof iconButtonVariants> {
  /** Accessible label for the icon (required for a11y) */
  "aria-label": string;
}

const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, variant, size, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        type="button"
        className={cn(iconButtonVariants({ variant, size }), className)}
        {...props}
      >
        {children}
      </button>
    );
  },
);
IconButton.displayName = "IconButton";

export { IconButton, iconButtonVariants };
