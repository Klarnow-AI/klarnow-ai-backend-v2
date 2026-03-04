"use client";

import { Check } from "@/components/icons";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DAY_TITLES } from "@/lib/sprint-phases";
import type { DayCardRead, SprintRead } from "@/types/api-types";

interface SprintDayCardProps {
  dayCard: DayCardRead;
  sprint: SprintRead;
  onDayClick: (dayNumber: number) => void;
}

function getStatus(dayCard: DayCardRead, currentDay: number): "completed" | "in_progress" | "pending" {
  if (dayCard.completed_at) return "completed";
  if (dayCard.day_number === currentDay) return "in_progress";
  return "pending";
}

export function SprintDayCard({ dayCard, sprint, onDayClick }: SprintDayCardProps) {
  const status = getStatus(dayCard, sprint.current_day);
  const isClickable =
    status === "in_progress" ||
    (status === "completed" && dayCard.day_number <= 3) ||
    (status === "pending" && dayCard.day_number <= sprint.current_day);
  const isLocked = status === "pending" && dayCard.day_number > sprint.current_day;

  const handleClick = () => {
    if (isLocked) return;
    if (isClickable) onDayClick(dayCard.day_number);
  };

  return (
    <Card
      className={cn(
        "flex flex-col p-4 transition-all min-h-[140px]",
        isClickable && "cursor-pointer hover:shadow-md",
        isLocked && "cursor-not-allowed opacity-60",
        status === "completed" && "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800",
        status === "in_progress" && "bg-primary/5 border-primary",
      )}
      onClick={handleClick}
    >
      <div className="flex flex-1 flex-col">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold">
              Step {dayCard.day_number}: {DAY_TITLES[dayCard.day_number]}
            </span>
            {status === "in_progress" && (
              <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs font-medium text-primary">
                Today
              </span>
            )}
          </div>
          <div className="shrink-0">
            {status === "completed" ? (
              <Check className="h-5 w-5 text-green-600" />
            ) : (
              <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/60" />
            )}
          </div>
        </div>
        <div className="mt-auto pt-4">
          <Button
            variant={status === "pending" ? "outline" : "default"}
            size="sm"
            className={cn(
              "w-full",
              status === "pending" && "bg-muted/50 text-muted-foreground",
            )}
            disabled={isLocked}
          >
            {status === "completed" && "Completed"}
            {status === "in_progress" && "In Progress"}
            {status === "pending" && "Pending"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
