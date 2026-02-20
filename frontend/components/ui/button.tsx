"use client";

import { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] hover:active:scale-[0.98]",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
        secondary:
          "bg-secondary text-secondary-foreground border border-border hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
        ghost:
          "hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
        outline:
          "border-2 border-white/40 bg-transparent text-primary hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
        destructive:
          "bg-white/20 text-foreground border border-border hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
      },
      size: {
        sm: "h-9 px-4 text-sm",
        md: "h-11 px-6 text-sm",
        lg: "h-12 px-8 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      >
        {props.children}
      </button>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
