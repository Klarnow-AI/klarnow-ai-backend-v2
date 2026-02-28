"use client";

import { SPRINT_PHASES, getPhaseForDay } from "@/lib/sprint-phases";
import { SprintDayCard } from "./sprint-day-card";
import { Star } from "@/components/icons";
import type { SprintRead } from "@/types/api-types";

interface SprintTimelineViewProps {
  sprint: SprintRead;
  onDayClick: (dayNumber: number) => void;
}

export function SprintTimelineView({ sprint, onDayClick }: SprintTimelineViewProps) {
  const dayCardsByNumber = new Map(sprint.day_cards.map((c) => [c.day_number, c]));

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 15 }, (_, i) => i).map((dayNumber) => {
        const dayCard = dayCardsByNumber.get(dayNumber);
        if (!dayCard) return null;

        const phase = getPhaseForDay(dayNumber);
        const prevPhase = dayNumber > 0 ? getPhaseForDay(dayNumber - 1) : null;
        const showPhaseDivider = phase && prevPhase && phase.id !== prevPhase.id;

        return (
          <div key={dayNumber} className="contents">
            {showPhaseDivider && (
              <div className="col-span-full mt-6 mb-2">
                <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-4 py-2 w-fit">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Phase
                  </span>
                  <Star className="h-4 w-4 text-amber-500" />
                  <span className="text-sm font-medium">{phase?.label}</span>
                </div>
              </div>
            )}
            <SprintDayCard
              dayCard={dayCard}
              sprint={sprint}
              onDayClick={onDayClick}
            />
          </div>
        );
      })}
    </div>
  );
}
