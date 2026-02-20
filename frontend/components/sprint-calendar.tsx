"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Check, AlertCircle, Lock } from "@/components/icons";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface DayCard {
  id: string;
  day_number: number;
  completed_at: string | null;
  outreach_count: number;
  followup_count: number;
  proof_logged: boolean;
  output_shipped: boolean;
}

interface Sprint {
  id: string;
  mode: string;
  current_day: number;
  started_at: string;
  day_cards: DayCard[];
}

interface SprintCalendarProps {
  sprint: Sprint;
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
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  
  if (formatStr === "MMMM yyyy") {
    return `${months[date.getMonth()]} ${date.getFullYear()}`;
  } else if (formatStr === "d") {
    return date.getDate().toString();
  } else if (formatStr === "yyyy-MM-dd") {
    return date.toISOString().split('T')[0];
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
  return date1.getMonth() === date2.getMonth() && date1.getFullYear() === date2.getFullYear();
}

function addMonthsFn(date: Date, months: number): Date {
  const newDate = new Date(date);
  newDate.setMonth(newDate.getMonth() + months);
  return newDate;
}

export function SprintCalendar({ sprint, onDayClick }: SprintCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date());

  const monthStart = getStartOfMonth(currentMonth);
  const monthEnd = getEndOfMonth(currentMonth);
  const daysInMonth = getDaysInMonth(currentMonth);

  // Map sprint days to calendar dates (starting from sprint start date)
  const sprintStartDate = new Date(sprint.started_at);
  
  const getDayCardForDate = (date: Date): DayCard | null => {
    const daysSinceStart = Math.floor((date.getTime() - sprintStartDate.getTime()) / (1000 * 60 * 60 * 24));
    if (daysSinceStart >= 0 && daysSinceStart <= 14) {
      return sprint.day_cards.find(card => card.day_number === daysSinceStart) || null;
    }
    return null;
  };

  const getProgressPercentage = (card: DayCard): number => {
    if (card.completed_at) return 100;
    if (card.day_number < 4 || card.day_number > 13) return 0;
    
    let completed = 0;
    let total = 4;
    
    if (card.output_shipped) completed++;
    if (card.proof_logged) completed++;
    if (card.outreach_count >= 10) completed++; // Simplified target
    if (card.followup_count >= 5) completed++; // Simplified target
    
    return (completed / total) * 100;
  };

  return (
    <div className="w-full space-y-4">
      {/* Calendar Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">
            {formatDate(currentMonth, "MMMM yyyy")}
          </h2>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={sprint.mode === "build" ? "default" : "secondary"}>
              {sprint.mode === "build" ? "Build Mode" : "Improve Mode"}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Day {sprint.current_day} of 14
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setCurrentMonth(addMonthsFn(currentMonth, -1))}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setCurrentMonth(addMonthsFn(currentMonth, 1))}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Day of Week Headers */}
      <div className="grid grid-cols-7 gap-2">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
          <div
            key={day}
            className="text-center text-sm font-medium text-muted-foreground py-2"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-2">
        {/* Empty cells for days before month starts */}
        {Array.from({ length: monthStart.getDay() }).map((_, i) => (
          <div key={`empty-${i}`} className="aspect-square" />
        ))}

        {/* Days */}
        {daysInMonth.map((date) => {
          const dayCard = getDayCardForDate(date);
          const isToday = formatDate(date, "yyyy-MM-dd") === formatDate(new Date(), "yyyy-MM-dd");
          const isSprintDay = dayCard !== null;
          const isCompleted = !!dayCard?.completed_at;
          const isCurrent = dayCard?.day_number === sprint.current_day;
          const isLocked = isSprintDay && dayCard != null && dayCard.day_number > sprint.current_day && !dayCard.completed_at;
          const isClickable = isSprintDay && !isLocked && !isCompleted;
          const progress = dayCard ? getProgressPercentage(dayCard) : 0;

          return (
            <Card
              key={date.toISOString()}
              className={cn(
                "aspect-square p-2 transition-all",
                isClickable && "cursor-pointer hover:shadow-md",
                isLocked && "cursor-not-allowed opacity-60",
                !isSprintDay && "cursor-default hover:shadow-none",
                !isSameMonthFn(date, currentMonth) && "opacity-50",
                isToday && "ring-2 ring-primary",
                isCurrent && "bg-primary/5 border-primary",
                isCompleted && "bg-green-50 dark:bg-green-950/20",
              )}
              onClick={() => isClickable && dayCard && onDayClick(dayCard.day_number)}
              title={isLocked ? `Complete Day ${sprint.current_day} first` : undefined}
            >
              <div className="flex flex-col h-full">
                <div className="flex items-start justify-between mb-1">
                  <span
                    className={cn(
                      "text-sm font-medium",
                      isToday && "text-primary font-bold"
                    )}
                  >
                    {formatDate(date, "d")}
                  </span>
                  {isSprintDay && (
                    <div>
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
                  <div className="flex-1 flex flex-col justify-between">
                    <div>
                      <div className={cn(
                        "text-xs font-semibold mb-1",
                        isLocked ? "text-muted-foreground/60" : "text-primary",
                      )}>
                        Day {dayCard.day_number}
                      </div>
                      <div className="text-xs text-muted-foreground line-clamp-2">
                        {DAY_TITLES[dayCard.day_number]}
                      </div>
                    </div>

                    {!isCompleted && !isLocked && dayCard.day_number >= 4 && dayCard.day_number <= 13 && (
                      <Progress value={progress} className="h-1 mt-2" />
                    )}
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 pt-4 border-t">
        <div className="flex items-center gap-2">
          <Check className="h-4 w-4 text-green-600" />
          <span className="text-sm text-muted-foreground">Completed</span>
        </div>
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-primary" />
          <span className="text-sm text-muted-foreground">Current Day</span>
        </div>
        <div className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-muted-foreground/60" />
          <span className="text-sm text-muted-foreground">Locked</span>
        </div>
      </div>
    </div>
  );
}
