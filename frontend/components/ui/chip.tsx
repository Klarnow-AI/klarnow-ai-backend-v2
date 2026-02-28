"use client";

import { forwardRef } from "react";
import Link from "next/link";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const chipVariants = cva(
  "inline-flex items-center gap-2 font-medium text-foreground border-0 bg-border/40 rounded-full transition-all hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black hover:scale-105 focus-visible:outline-none focus-visible:scale-105 focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1 cursor-pointer",
  {
    variants: {
      size: {
        sm: "gap-1.5 px-3 py-1.5 text-sm",
        md: "gap-2 px-4 py-2.5 text-sm",
      },
    },
    defaultVariants: {
      size: "sm",
    },
  },
);

export interface ChipProps
  extends
    Omit<
      React.AnchorHTMLAttributes<HTMLAnchorElement> &
        React.ButtonHTMLAttributes<HTMLButtonElement>,
      "children"
    >,
    VariantProps<typeof chipVariants> {
  /** Optional leading icon component */
  icon?: React.ReactNode;
  /** Optional trailing icon/content (e.g. ChevronDown) */
  trailing?: React.ReactNode;
  children: React.ReactNode;
  /** When set, renders as Next.js Link with this href */
  href?: string;
}

const Chip = forwardRef<HTMLButtonElement | HTMLAnchorElement, ChipProps>(
  (
    {
      className,
      icon,
      trailing,
      children,
      href,
      size,
      type = "button",
      ...rest
    },
    ref,
  ) => {
    const content = (
      <>
        {icon && (
          <span className="shrink-0 [&>svg]:h-4 [&>svg]:w-4">{icon}</span>
        )}
        {children}
        {trailing && (
          <span className="shrink-0 [&>svg]:h-4 [&>svg]:w-4 [&>svg]:opacity-60">
            {trailing}
          </span>
        )}
      </>
    );

    const classes = cn(
      chipVariants({ size }),
      href && "no-underline",
      className,
    );

    if (href) {
      return (
        <Link
          ref={ref as React.Ref<HTMLAnchorElement>}
          href={href}
          className={classes}
          {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}
        >
          {content}
        </Link>
      );
    }

    return (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        type={type}
        className={classes}
        {...(rest as React.ButtonHTMLAttributes<HTMLButtonElement>)}
      >
        {content}
      </button>
    );
  },
);
Chip.displayName = "Chip";

export { Chip, chipVariants };
