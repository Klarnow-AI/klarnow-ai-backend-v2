"use client";

import { Check } from "@/components/icons";
import { Button } from "@/components/ui/button";

interface OutreachLoggerProps {
  /** Current count for this sprint day */
  count: number;
  /** Target to reach (e.g. 20) */
  target: number;
  /** Call API to log +1 */
  onLog: (increment?: number) => Promise<void>;
  /** Refreshing state */
  disabled?: boolean;
}

export function OutreachLogger({
  count,
  target,
  onLog,
  disabled = false,
}: OutreachLoggerProps) {
  const met = count >= target;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-muted-foreground">Outreach:</span>
      <span className="text-sm font-medium">
        {count} / {target}
      </span>
      {met ? (
        <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
          <Check className="h-4 w-4" /> Done
        </span>
      ) : (
        <>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onLog(1)}
            disabled={disabled}
          >
            +1
          </Button>
          {target - count >= 5 && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onLog(5)}
              disabled={disabled}
            >
              +5
            </Button>
          )}
        </>
      )}
    </div>
  );
}
