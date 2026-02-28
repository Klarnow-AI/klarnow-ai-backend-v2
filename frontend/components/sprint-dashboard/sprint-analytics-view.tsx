"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { SprintRead } from "@/types/api-types";

interface SprintAnalyticsViewProps {
  sprint: SprintRead;
}

export function SprintAnalyticsView({ sprint }: SprintAnalyticsViewProps) {
  const completedCount = sprint.day_cards.filter((c) => c.completed_at).length;
  const totalOutreach = sprint.day_cards.reduce((sum, c) => sum + c.outreach_count, 0);
  const totalFollowup = sprint.day_cards.reduce((sum, c) => sum + c.followup_count, 0);

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Basic sprint metrics. Full analytics coming soon.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">Days completed</CardTitle>
            <CardDescription>Out of 15 total days</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{completedCount} / 15</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">Outreach logged</CardTitle>
            <CardDescription>Across all sprint days</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{totalOutreach}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">Follow-ups logged</CardTitle>
            <CardDescription>Across all sprint days</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{totalFollowup}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
