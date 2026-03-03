"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { SprintRead } from "@/types/api-types";

interface SprintAnalyticsViewProps {
  sprint: SprintRead;
}

export function SprintAnalyticsView({ sprint }: SprintAnalyticsViewProps) {
  const completedCount = sprint.day_cards.filter((c) => c.completed_at).length;

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Sprint metrics summary.
      </p>
      <div className="grid grid-cols-1 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">Days completed</CardTitle>
            <CardDescription>Out of 15 total days</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{completedCount} / 15</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
