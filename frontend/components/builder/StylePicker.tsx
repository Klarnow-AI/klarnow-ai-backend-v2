"use client";

import { useState } from "react";
import { useProjectStore } from "@/store/useProjectStore";
import { Button } from "@/components/ui/button";
import { ChevronRight } from "@/components/icons";
import { cn } from "@/lib/utils";
import { designSystems, type DesignSystemKey } from "@/lib/designSystems";

const STYLE_KEYS = Object.keys(designSystems) as DesignSystemKey[];

export function StylePicker() {
  const [selected, setSelected] = useState<DesignSystemKey | null>(null);
  const setSelectedStyle = useProjectStore((s) => s.setSelectedStyle);

  const handleConfirm = () => {
    if (!selected) return;
    setSelectedStyle(selected);
  };

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-6">
      <div className="text-center mb-6">
        <h2 className="text-base font-semibold text-foreground mb-1">
          Choose a style
        </h2>
        <p className="text-sm text-muted-foreground">
          Pick a design direction — you can always refine later.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
        {STYLE_KEYS.map((key) => {
          const system = designSystems[key];
          const isSelected = selected === key;

          return (
            <button
              key={key}
              type="button"
              onClick={() => setSelected(key)}
              className={cn(
                "relative flex flex-col gap-2 rounded-xl border p-3 text-left transition-all",
                "hover:border-foreground/30",
                isSelected ? "border-primary/50 scale-105" : "border-border",
              )}
            >
              <div className={cn("h-8 w-full rounded-md", system.preview)} />
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "h-2.5 w-2.5 rounded-full shrink-0",
                    system.dot,
                  )}
                />
                <span
                  className={cn(
                    "text-xs truncate",
                    isSelected
                      ? " font-[600] text-primary"
                      : "font-medium text-foreground",
                  )}
                >
                  {system.name}
                </span>
              </div>
              <p className="text-[11px] leading-tight text-muted-foreground">
                {system.description}
              </p>
            </button>
          );
        })}
      </div>

      <Button
        size="md"
        disabled={!selected}
        onClick={handleConfirm}
        className="mt-6 gap-2"
      >
        Start building
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
