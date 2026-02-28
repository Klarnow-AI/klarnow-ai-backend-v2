"use client";

import { cn } from "@/lib/utils";
import { BentoGrid, BentoItem } from "@/components/ui/bento-grid";
import type { BentoSize } from "@/components/ui/bento-grid";
import type { BrandShowcaseItem } from "@/types/api-types";

export interface BrandShowcaseGridProps {
  items: BrandShowcaseItem[];
  hasLogo: boolean;
  onAddLogo?: () => void;
  onGenerateMockups?: () => void;
  mockupsLoading?: boolean;
}

function ColorSwatch({ value }: { value: string }) {
  const cssColor = /^#|^rgb|^hsl/.test(value)
    ? value
    : `#${value.replace(/^#/, "")}`;
  return (
    <div
      className="h-6 w-8 rounded border border-white/20 shrink-0"
      style={{ backgroundColor: cssColor }}
      title={value}
    />
  );
}

function EmptyState({
  message,
  buttonLabel,
  onAction,
  loading,
}: {
  message: string;
  buttonLabel?: string;
  onAction?: () => void;
  loading?: boolean;
}) {
  return (
    <div className="flex h-full min-h-[280px] flex-col items-center justify-center rounded-2xl border border-border border-dashed bg-muted/30 p-8 text-center">
      <p className="text-sm font-medium text-foreground">{message}</p>
      {onAction && buttonLabel && (
        <button
          type="button"
          onClick={onAction}
          disabled={loading}
          className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Generating…" : buttonLabel}
        </button>
      )}
    </div>
  );
}

export function BrandShowcaseGrid({
  items,
  hasLogo,
  onAddLogo,
  onGenerateMockups,
  mockupsLoading = false,
}: BrandShowcaseGridProps) {
  if (!hasLogo) {
    return (
      <EmptyState
        message="Add a logo to generate brand mockups."
        buttonLabel="Add logo"
        onAction={onAddLogo}
      />
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        message="Generate mockups to see them here."
        buttonLabel="Generate mockups"
        onAction={onGenerateMockups}
        loading={mockupsLoading}
      />
    );
  }

  const noMockupsYet = items.every(
    (i) => i.type === "logo" || i.type === "svg",
  );

  let tallUsed = false;

  return (
    <BentoGrid>
      {items.map((item) => {
        const isLogo = item.type === "logo" || item.type === "svg";
        const isSvg =
          item.src &&
          typeof item.src === "string" &&
          item.src.trimStart().startsWith("<");

        let size: BentoSize = isLogo
          ? "medium"
          : (item.size as BentoSize) || "medium";

        if (size === "tall") {
          if (tallUsed) {
            size = "medium";
          } else {
            tallUsed = true;
          }
        }

        return (
          <BentoItem
            key={item.id}
            size={size}
            className={cn(
              isLogo &&
                "flex-col items-center justify-center bg-[#faf8f5] dark:bg-black",
              item.type === "image" && "p-0",
              item.type === "text" && "flex-col justify-center p-4",
            )}
          >
            {item.type === "text" && (
              <>
                {item.label && (
                  <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-1">
                    {item.label}
                  </p>
                )}
                {item.sublabel && (
                  <p className="text-sm font-semibold text-foreground line-clamp-2 break-words">
                    {item.sublabel}
                  </p>
                )}
                {item.colorSwatches && item.colorSwatches.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {item.colorSwatches.slice(0, 5).map((swatch, i) => (
                      <ColorSwatch key={i} value={swatch.value} />
                    ))}
                  </div>
                )}
              </>
            )}

            {isLogo && item.src && (
              <div className="w-full h-full flex items-center justify-center">
                {isSvg ? (
                  <div
                    className="w-full max-w-full h-full max-h-full flex items-center justify-center [&>svg]:max-w-full [&>svg]:max-h-full [&>svg]:text-foreground"
                    dangerouslySetInnerHTML={{ __html: item.src }}
                  />
                ) : (
                  <img
                    src={item.src}
                    alt={item.alt ?? "Brand logo"}
                    className="max-w-full max-h-full w-full h-full object-contain"
                  />
                )}
              </div>
            )}

            {item.type === "image" && item.src && (
              <img
                src={item.src}
                alt={item.alt ?? ""}
                className="absolute inset-0 w-full h-full object-cover"
              />
            )}
          </BentoItem>
        );
      })}

      {noMockupsYet && onGenerateMockups && (
        <BentoItem
          size="medium"
          className="flex-col items-center justify-center border-dashed bg-muted/30 p-6 text-center"
        >
          <p className="text-sm font-medium text-foreground">
            Generate mockups to see them here.
          </p>
          <button
            type="button"
            onClick={onGenerateMockups}
            disabled={mockupsLoading}
            className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-50"
          >
            {mockupsLoading ? "Generating…" : "Generate mockups"}
          </button>
        </BentoItem>
      )}
    </BentoGrid>
  );
}
