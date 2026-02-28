"use client";

import { SPRINT_PHASES } from "@/lib/sprint-phases";
import { SprintDayCard } from "./sprint-day-card";
import { Star } from "@/components/icons";
import type { SprintRead } from "@/types/api-types";

interface SprintPhaseViewProps {
  sprint: SprintRead;
  onDayClick: (dayNumber: number) => void;
}

export function SprintPhaseView({ sprint, onDayClick }: SprintPhaseViewProps) {
  const dayCardsByNumber = new Map(sprint.day_cards.map((c) => [c.day_number, c]));

  return (
    <div className="space-y-10">
      {SPRINT_PHASES.map((phase) => {
        const phaseDayCards = phase.dayNumbers
          .map((n) => dayCardsByNumber.get(n))
          .filter(Boolean);
        if (phaseDayCards.length === 0) return null;

        return (
          <section key={phase.id} className="space-y-4">
            <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-4 py-2 w-fit">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Phase
              </span>
              <Star className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-medium">{phase.label}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {phaseDayCards.map((dayCard) => (
                <SprintDayCard
                  key={dayCard!.day_number}
                  dayCard={dayCard!}
                  sprint={sprint}
                  onDayClick={onDayClick}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
