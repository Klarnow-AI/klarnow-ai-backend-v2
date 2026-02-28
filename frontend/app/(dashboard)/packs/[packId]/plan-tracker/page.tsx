"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { buildChatUrlWithDay } from "@/app/(dashboard)/chat/helpers";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/page-loader";
import { sprintApi } from "@/api_requests/sprint";
import type { SprintRead } from "@/types/api-types";
import { SprintTimelineView } from "@/components/sprint-dashboard/sprint-timeline-view";
import { SprintPhaseView } from "@/components/sprint-dashboard/sprint-phase-view";
import { SprintAnalyticsView } from "@/components/sprint-dashboard/sprint-analytics-view";
import { DayDetailModal } from "@/components/day-detail-modal";
import { cn } from "@/lib/utils";

export default function PlanTrackerPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const packId = params.packId as string;
  const [sprint, setSprint] = useState<SprintRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dayModalOpen, setDayModalOpen] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"timeline" | "phase" | "analytics">("timeline");
  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const loadSprint = useCallback(() => {
    cancelRef.current?.();
    let cancelled = false;
    cancelRef.current = () => {
      cancelled = true;
    };
    setError("");
    sprintApi
      .getSprint(packId)
      .then((data) => {
        if (!cancelled) setSprint(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load sprint");
        setSprint(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
  }, [packId]);

  useEffect(() => {
    loadSprint();
    return () => {
      cancelRef.current?.();
    };
  }, [loadSprint]);

  const dayFromUrl = searchParams.get("day");
  useEffect(() => {
    if (dayFromUrl === null) return;
    const n = parseInt(dayFromUrl, 10);
    if (Number.isInteger(n) && n >= 0 && n <= 3) {
      router.replace(buildChatUrlWithDay(packId, n));
      return;
    }
    if (Number.isInteger(n) && n >= 4 && n <= 14) {
      setDayModalOpen(n);
    }
  }, [dayFromUrl, packId, router]);

  const handleStartSprint = async () => {
    setError("");
    try {
      const newSprint = await sprintApi.createSprint(packId);
      setSprint(newSprint);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start sprint");
    }
  };

  const openDayModal = (dayNumber: number) => {
    setDayModalOpen(dayNumber);
    const url = new URL(window.location.href);
    url.searchParams.set("day", String(dayNumber));
    router.replace(url.pathname + "?" + url.searchParams.toString(), {
      scroll: false,
    });
  };

  const closeDayModal = () => {
    setDayModalOpen(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("day");
    const q = url.searchParams.toString();
    router.replace(q ? url.pathname + "?" + q : url.pathname, {
      scroll: false,
    });
  };

  const handleDayComplete = () => {
    setDayModalOpen(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("day");
    const q = url.searchParams.toString();
    router.replace(q ? url.pathname + "?" + q : url.pathname, {
      scroll: false,
    });
    loadSprint();
    router.refresh();
  };

  const handleDayClick = (dayNumber: number) => {
    if (dayNumber >= 0 && dayNumber <= 3) {
      router.push(buildChatUrlWithDay(packId, dayNumber));
      return;
    }
    openDayModal(dayNumber);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="w-full max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-[600] tracking-tight">
            Sprint Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            14-day structured sprint from clarity to revenue
          </p>
        </div>
        {sprint && (
          <Button variant="secondary" size="md" className="shrink-0">
            Sprint 1
          </Button>
        )}
      </motion.div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-500/10 text-red-600 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {!sprint ? (
        <Card asMotion delay={0.1}>
          <CardHeader>
            <CardTitle>No active sprint</CardTitle>
            <CardDescription>
              Start a 14-day sprint to get your personalized plan with Build or
              Improve mode based on your business stage.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleStartSprint} size="lg">
              Start 14-day sprint
            </Button>
          </CardContent>
        </Card>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="space-y-6"
        >
          <div className="space-y-2">
            <p className="text-sm font-medium">Overall Progress</p>
            <div className="flex items-center gap-4">
              <Progress
                value={(sprint.day_cards.filter((c) => c.completed_at).length / 15) * 100}
                className="flex-1 h-2"
              />
              <span className="text-sm text-muted-foreground shrink-0">
                {sprint.day_cards.filter((c) => c.completed_at).length} of 15 days
              </span>
            </div>
          </div>

          <div className="flex gap-2 border-b border-border pb-2">
            {(["timeline", "phase", "analytics"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
                  activeTab === tab
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                )}
              >
                {tab === "timeline" && "Timeline"}
                {tab === "phase" && "By Phase"}
                {tab === "analytics" && "Analytics"}
              </button>
            ))}
          </div>

          {activeTab === "timeline" && (
            <SprintTimelineView sprint={sprint} onDayClick={handleDayClick} />
          )}
          {activeTab === "phase" && (
            <SprintPhaseView sprint={sprint} onDayClick={handleDayClick} />
          )}
          {activeTab === "analytics" && <SprintAnalyticsView sprint={sprint} />}
        </motion.div>
      )}

      {dayModalOpen !== null && dayModalOpen >= 4 && dayModalOpen <= 14 && (
        <DayDetailModal
          packId={packId}
          dayNumber={dayModalOpen}
          open={true}
          onClose={closeDayModal}
          onComplete={handleDayComplete}
        />
      )}
    </div>
  );
}
