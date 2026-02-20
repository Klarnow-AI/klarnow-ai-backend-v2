"use client";

import { Check } from "@/components/icons";
import { Button } from "@/components/ui/button";

interface OutputShippedLoggerProps {
  /** Whether output has been marked shipped for this day */
  shipped: boolean;
  /** Call API to mark output shipped */
  onMarkShipped: () => Promise<void>;
  disabled?: boolean;
}

export function OutputShippedLogger({
  shipped,
  onMarkShipped,
  disabled = false,
}: OutputShippedLoggerProps) {
  if (shipped) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Output shipped:</span>
        <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
          <Check className="h-4 w-4" /> Done
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">Output shipped:</span>
      <Button size="sm" variant="outline" onClick={onMarkShipped} disabled={disabled}>
        I&apos;ve shipped today&apos;s output
      </Button>
    </div>
  );
}
