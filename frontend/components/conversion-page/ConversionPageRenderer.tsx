"use client";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LeadCaptureForm } from "./LeadCaptureForm";

type AnyRecord = Record<string, unknown>;

type Section = {
  type?: string;
  componentType?: string;
  props?: AnyRecord;
  [key: string]: unknown;
};

function coerceSections(structure: AnyRecord | AnyRecord[] | null): Section[] {
  if (!structure) return [];
  if (Array.isArray(structure)) return structure as Section[];
  const s = (structure as AnyRecord).sections;
  if (Array.isArray(s)) return s as Section[];
  return [];
}

function sectionType(section: Section): string {
  return String(section.type ?? section.componentType ?? "");
}

function getProps(section: Section): AnyRecord {
  const p = section.props;
  return p && typeof p === "object" ? (p as AnyRecord) : {};
}

export function ConversionPageRenderer({
  packId,
  structure,
  mode = "public",
}: {
  packId: string;
  structure: AnyRecord | AnyRecord[] | null;
  mode?: "public" | "preview";
}) {
  const sections = coerceSections(structure);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto w-full max-w-3xl px-5 py-12 sm:px-6">
        <div className="space-y-10">
          {sections.length === 0 ? (
            <div className="rounded-2xl border border-border bg-card p-8">
              <h1 className="text-2xl font-semibold">No content yet</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                This page doesn’t have any sections to render.
              </p>
            </div>
          ) : (
            sections.map((section, idx) => (
              <RenderSection
                key={`${sectionType(section)}-${idx}`}
                packId={packId}
                section={section}
                mode={mode}
              />
            ))
          )}
        </div>
      </div>
    </main>
  );
}

function RenderSection({
  packId,
  section,
  mode,
}: {
  packId: string;
  section: Section;
  mode: "public" | "preview";
}) {
  const t = sectionType(section);
  const props = getProps(section);

  if (t === "hero") {
    const headline = String(props.headline ?? "Your headline");
    const subheadline = String(props.subheadline ?? "");
    const backgroundImage = props.backgroundImage ? String(props.backgroundImage) : null;
    const gradientFrom = props.gradientFrom ? String(props.gradientFrom) : null;
    const gradientTo = props.gradientTo ? String(props.gradientTo) : null;
    
    // Build background style
    let backgroundStyle: React.CSSProperties = {};
    if (backgroundImage) {
      backgroundStyle = {
        backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url(${backgroundImage})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      };
    } else if (gradientFrom && gradientTo) {
      backgroundStyle = {
        backgroundImage: `linear-gradient(135deg, ${gradientFrom}, ${gradientTo})`,
      };
    }
    
    const hasBackground = backgroundImage || (gradientFrom && gradientTo);
    
    return (
      <section 
        className={cn(
          "space-y-4 rounded-2xl p-8",
          hasBackground ? "text-white" : ""
        )}
        style={backgroundStyle}
      >
        <h1 className={cn(
          "text-4xl font-bold tracking-tight sm:text-5xl",
          hasBackground ? "text-white" : ""
        )} style={{ fontFamily: "var(--font-heading, inherit)" }}>
          {headline}
        </h1>
        {subheadline && (
          <p className={cn(
            "text-base sm:text-lg",
            hasBackground ? "text-white/90" : "text-muted-foreground"
          )} style={{ fontFamily: "var(--font-body, inherit)" }}>
            {subheadline}
          </p>
        )}
      </section>
    );
  }

  if (t === "benefits") {
    const title = String(props.title ?? "Benefits");
    const itemsRaw = props.items;
    const items: Array<{ text?: string; title?: string; description?: string; icon?: string }> = Array.isArray(
      itemsRaw
    )
      ? itemsRaw.map((x) => {
          if (typeof x === "string") return { text: x };
          if (x && typeof x === "object") {
            const o = x as AnyRecord;
            return {
              text: o.text ? String(o.text) : undefined,
              title: String(o.title ?? o.label ?? ""),
              description: o.description ? String(o.description) : undefined,
              icon: o.icon ? String(o.icon) : undefined,
            };
          }
          return { text: "Benefit" };
        })
      : [];

    return (
      <section className="rounded-2xl border border-border bg-card p-6">
        <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading, inherit)" }}>{title}</h2>
        {items.length > 0 ? (
          <ul className="mt-4 space-y-3">
            {items.map((it, i) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                {it.icon && <span className="text-xl">{it.icon}</span>}
                <div className="flex-1">
                  <p className="font-medium" style={{ fontFamily: "var(--font-body, inherit)" }}>
                    {it.text || it.title}
                  </p>
                  {it.description && (
                    <p className="mt-0.5 text-muted-foreground">
                      {it.description}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-muted-foreground">No benefits yet.</p>
        )}
      </section>
    );
  }

  if (t === "socialProof") {
    const title = String(props.title ?? "Social proof");
    const quotesRaw = props.quotes ?? props.items;
    const quotes: Array<{ quote: string; name?: string }> = Array.isArray(
      quotesRaw
    )
      ? quotesRaw.map((x) => {
          if (typeof x === "string") return { quote: x };
          if (x && typeof x === "object") {
            const o = x as AnyRecord;
            return {
              quote: String(o.quote ?? o.text ?? "Testimonial"),
              name: o.name ? String(o.name) : undefined,
            };
          }
          return { quote: "Testimonial" };
        })
      : [];

    return (
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">{title}</h2>
        {quotes.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {quotes.map((q, i) => (
              <figure
                key={i}
                className="rounded-2xl border border-border bg-card p-5"
              >
                <blockquote className="text-sm text-foreground">
                  “{q.quote}”
                </blockquote>
                {q.name && (
                  <figcaption className="mt-2 text-xs text-muted-foreground">
                    — {q.name}
                  </figcaption>
                )}
              </figure>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No testimonials yet.</p>
        )}
      </section>
    );
  }

  if (t === "leadForm") {
    const headline = props.headline ? String(props.headline) : undefined;
    const subheadline = props.subheadline ? String(props.subheadline) : undefined;
    return (
      <section>
        <LeadCaptureForm
          packId={packId}
          enabled={mode === "public"}
          headline={headline}
          subheadline={subheadline}
        />
      </section>
    );
  }

  if (t === "cta") {
    const label = String(props.label ?? "Get started");
    const href = typeof props.href === "string" ? props.href : "#lead";
    const headline = props.headline ? String(props.headline) : "Ready?";
    const subheadline = props.subheadline ? String(props.subheadline) : "";
    return (
      <section className="rounded-2xl border border-border bg-card p-6">
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading, inherit)" }}>{headline}</h2>
            {subheadline && (
              <p className="mt-1 text-sm text-muted-foreground" style={{ fontFamily: "var(--font-body, inherit)" }}>
                {subheadline}
              </p>
            )}
          </div>
          <a
            href={href}
            className={cn(buttonVariants({ variant: "default", size: "lg" }))}
            style={{ 
              backgroundColor: "var(--color-primary, #6366f1)",
              fontFamily: "var(--font-body, inherit)"
            }}
          >
            {label}
          </a>
        </div>
      </section>
    );
  }

  // Unknown section type: ignore but keep visible in preview for debugging.
  if (mode === "preview") {
    return (
      <section className="rounded-2xl border border-dashed border-border bg-card p-6">
        <p className="text-sm text-muted-foreground">
          Unknown section type: <span className="font-mono">{t || "?"}</span>
        </p>
      </section>
    );
  }

  return null;
}

