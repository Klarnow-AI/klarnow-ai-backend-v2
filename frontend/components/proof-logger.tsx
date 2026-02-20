"use client";

import { Check } from "@/components/icons";
import { Button } from "@/components/ui/button";

interface ProofLoggerProps {
  /** Whether proof has been logged for this day */
  logged: boolean;
  /** Call API to log proof */
  onLog: () => Promise<void>;
  disabled?: boolean;
}

export function ProofLogger({ logged, onLog, disabled = false }: ProofLoggerProps) {
  if (logged) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Proof:</span>
        <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
          <Check className="h-4 w-4" /> Logged
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">Proof:</span>
      <Button size="sm" variant="outline" onClick={onLog} disabled={disabled}>
        Log proof
      </Button>
    </div>
  );
}
