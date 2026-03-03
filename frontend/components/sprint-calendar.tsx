"use client";

import { useMemo, useRef, useEffect } from "react";
import { Check, AlertCircle, Lock } from "@/components/icons";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { SprintRead, DayCardRead } from "@/types/api-types";

interface SprintCalendarProps {
  sprint: SprintRead;
  onDayClick: (dayNumber: number) => void;
}

const DAY_TITLES = [
  "Foundation",
  "Offer",
  "USP + Audience",
  "Confidence Script",
  "Ad Factory",
  "Posters",
  "Conversion Destination",
  "Publish / Confirm",
  "Response Rules",
  "Follow-up",
  "Fix the Leak",
  "Close Path",
  "Close Conversations",
  "Invoice / Payment",
  "Check-in",
];

// Helper functions to replace date-fns
function formatDate(date: Date, formatStr: string): string {
  const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  if (formatStr === "MMMM yyyy") {
    return `${months[date.getMonth()]} ${date.getFullYear()}`;
  } else if (formatStr === "d") {
    return date.getDate().toString();
  } else if (formatStr === "yyyy-MM-dd") {
    return date.toISOString().split("T")[0];
  }
  return date.toLocaleDateString();
}

function getStartOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function getEndOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function getDaysInMonth(date: Date): Date[] {
  const start = getStartOfMonth(date);
  const end = getEndOfMonth(date);
  const days: Date[] = [];

  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    days.push(new Date(d));
  }

  return days;
}

function isSameMonthFn(date1: Date, date2: Date): boolean {
  return (
    date1.getMonth() === date2.getMonth() &&
    date1.getFullYear() === date2.getFullYear()
  );
}

function addMonthsFn(date: Date, months: number): Date {
  const newDate = new Date(date);
  newDate.setMonth(newDate.getMonth() + months);
  return newDate;
}

export function SprintCalendar({ sprint, onDayClick }: SprintCalendarProps) {
  const sprintStartDate = new Date(sprint.started_at);
  const todayRef = useRef<HTMLDivElement>(null);

  // Scroll so current date is in view on mount
  useEffect(() => {
    todayRef.current?.scrollIntoView({ block: "center", behavior: "auto" });
  }, []);

  // Months to show: one before sprint start through two months after (covers 14-day sprint + buffer)
  const monthsToShow = useMemo(() => {
    const start = addMonthsFn(getStartOfMonth(sprintStartDate), -1);
    const months: Date[] = [];
    for (let i = 0; i < 4; i++) {
      months.push(addMonthsFn(start, i));
    }
    return months;
  }, [sprint.started_at]);

  const getDayCardReadForDate = (date: Date): DayCardRead | null => {
    const daysSinceStart = Math.floor(
      (date.getTime() - sprintStartDate.getTime()) / (1000 * 60 * 60 * 24),
    );
    if (daysSinceStart >= 0 && daysSinceStart <= 14) {
      return (
        sprint.day_cards.find((card) => card.day_number === daysSinceStart) ||
        null
      );
    }
    return null;
  };

  return (
    <div className="w-full flex flex-col">
      {/* Fixed header: no month nav, just sprint info */}
      <div className="flex items-center gap-2 mb-3">
        <Badge variant={sprint.mode === "build" ? "default" : "secondary"}>
          {sprint.mode === "build" ? "Build Mode" : "Improve Mode"}
        </Badge>
        <span className="text-sm text-muted-foreground">
          Day {sprint.current_day} of 14
        </span>
      </div>

      {/* Single scrollable list: all months stacked */}
      <div className="flex-1 min-h-0 overflow-y-auto max-h-[70vh] space-y-6 pr-1">
        {monthsToShow.map((currentMonth) => {
          const monthStart = getStartOfMonth(currentMonth);
          const daysInMonth = getDaysInMonth(currentMonth);
          return (
            <section key={currentMonth.getTime()} className="space-y-2">
              <h3 className="text-lg font-semibold sticky top-0 bg-background py-1 z-10">
                {formatDate(currentMonth, "MMMM yyyy")}
              </h3>
              <div className="grid grid-cols-7 gap-1">
                {["S", "M", "T", "W", "T", "F", "S"].map((day, i) => (
                  <div
                    key={`${day}-${i}`}
                    className="text-center text-xs font-medium text-muted-foreground py-1"
                  >
                    {day}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-2">
                {Array.from({ length: monthStart.getDay() }).map((_, i) => (
                  <div
                    key={`empty-${currentMonth.getTime()}-${i}`}
                    className="aspect-square min-h-[60px]"
                  />
                ))}
                {daysInMonth.map((date) => {
                  const dayCard = getDayCardReadForDate(date);
                  const isToday =
                    formatDate(date, "yyyy-MM-dd") ===
                    formatDate(new Date(), "yyyy-MM-dd");
                  const isSprintDay = dayCard !== null;
                  const isCompleted = !!dayCard?.completed_at;
                  const isCurrent = dayCard?.day_number === sprint.current_day;
                  const isLocked =
                    isSprintDay &&
                    dayCard != null &&
                    dayCard.day_number > sprint.current_day &&
                    !dayCard.completed_at;
                  const isClickable = isSprintDay && !isLocked && !isCompleted;

                  return (
                    <Card
                      key={date.toISOString()}
                      ref={isToday ? todayRef : undefined}
                      className={cn(
                        "aspect-square p-2 transition-all flex flex-col min-h-[60px]",
                        isClickable && "cursor-pointer hover:shadow-md",
                        isLocked && "cursor-not-allowed opacity-60",
                        !isSprintDay && "cursor-default hover:shadow-none",
                        !isSameMonthFn(date, currentMonth) && "opacity-50",
                        isToday && "scale-105",
                        isCurrent && "bg-primary/5 border-primary",
                        isCompleted && "bg-green-50 dark:bg-green-950/20",
                      )}
                      onClick={() =>
                        isClickable && dayCard && onDayClick(dayCard.day_number)
                      }
                      title={
                        isLocked
                          ? `Complete Day ${sprint.current_day} first`
                          : undefined
                      }
                    >
                      <div className="flex flex-col h-full">
                        <div className="flex items-start justify-between mb-1">
                          <span
                            className={cn(
                              "text-sm font-medium",
                              isToday && "text-primary  font-[600]",
                            )}
                          >
                            {formatDate(date, "d")}
                          </span>
                          {isSprintDay && (
                            <div className="shrink-0">
                              {isCompleted ? (
                                <Check className="h-4 w-4 text-green-600" />
                              ) : isLocked ? (
                                <Lock className="h-4 w-4 text-muted-foreground/60" />
                              ) : isCurrent ? (
                                <AlertCircle className="h-4 w-4 text-primary" />
                              ) : (
                                <div className="h-4 w-4 rounded-full border-2 border-muted-foreground" />
                              )}
                            </div>
                          )}
                        </div>
                        {isSprintDay && dayCard && (
                          <div className="flex-1 flex flex-col justify-between min-h-0">
                            <div>
                              <div
                                className={cn(
                                  "text-xs font-semibold mb-0.5",
                                  isLocked
                                    ? "text-muted-foreground/60"
                                    : "text-primary",
                                )}
                              >
                                Day {dayCard.day_number}
                              </div>
                              <div className="text-xs text-muted-foreground line-clamp-2">
                                {DAY_TITLES[dayCard.day_number]}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 pt-4 mt-4 border-t shrink-0">
        <div className="flex items-center gap-2">
          <Check className="h-4 w-4 text-green-600 shrink-0" />
          <span className="text-sm text-muted-foreground">Completed</span>
        </div>
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-primary shrink-0" />
          <span className="text-sm text-muted-foreground">Current Day</span>
        </div>
        <div className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-muted-foreground/60 shrink-0" />
          <span className="text-sm text-muted-foreground">Locked</span>
        </div>
      </div>
    </div>
  );
}
