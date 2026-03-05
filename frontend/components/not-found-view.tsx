"use client";

import Link from "next/link";

type NotFoundViewProps = {
  code?: string;
  title?: string;
  description?: string;
  primaryHref?: string;
  primaryLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
  className?: string;
};

export function NotFoundView({
  code = "404",
  title = "Page not found",
  description = "The page you requested does not exist or is no longer available.",
  primaryHref = "/",
  primaryLabel = "Go to home",
  secondaryHref = "/packs",
  secondaryLabel = "Open packs",
  className,
}: NotFoundViewProps) {
  return (
    <div
      className={[
        "relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 py-16",
        className ?? "",
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,hsl(var(--primary)/0.12),transparent_55%),radial-gradient(circle_at_80%_0%,hsl(var(--foreground)/0.08),transparent_45%)]" />
      <div className="relative z-10 w-full max-w-xl rounded-3xl border border-border bg-card/90 p-8 text-center shadow-sm backdrop-blur sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-muted-foreground">
          {code}
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          {title}
        </h1>
        <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-muted-foreground sm:text-base">
          {description}
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href={primaryHref}
            className="inline-flex h-[50px] min-w-[170px] items-center justify-center rounded-full bg-primary px-8 text-sm font-medium text-primary-foreground transition-colors hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
          >
            {primaryLabel}
          </Link>
          <Link
            href={secondaryHref}
            className="inline-flex h-[50px] min-w-[170px] items-center justify-center rounded-full bg-border/40 px-8 text-sm font-medium text-foreground transition-colors hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
          >
            {secondaryLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}
