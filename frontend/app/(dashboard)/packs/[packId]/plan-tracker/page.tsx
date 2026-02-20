"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/page-loader";
import { sprintApi } from "@/api_requests/sprint";
import type { SprintRead } from "@/types/api-types";
import { SprintCalendar } from "@/components/sprint-calendar";
import { Day0Modal } from "@/components/day-0-modal";
import { Day1Modal } from "@/components/day-1-modal";
import { Day2Modal } from "@/components/day-2-modal";
import { Day3Modal } from "@/components/day-3-modal";
import { DayDetailModal } from "@/components/day-detail-modal";

export default function PlanTrackerPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const packId = params.packId as string;
  const [sprint, setSprint] = useState<SprintRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dayModalOpen, setDayModalOpen] = useState<number | null>(null);
  const cancelRef = useRef<(() => void) | undefined>(undefined);

  const loadSprint = useCallback(() => {
    cancelRef.current?.();
    let cancelled = false;
    cancelRef.current = () => { cancelled = true; };
    setError("");
    sprintApi
      .getSprint(packId)
      .then((data) => { if (!cancelled) setSprint(data); })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load sprint");
        setSprint(null);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
  }, [packId]);

  useEffect(() => {
    loadSprint();
    return () => { cancelRef.current?.(); };
  }, [loadSprint]);

  const dayFromUrl = searchParams.get("day");
  useEffect(() => {
    if (dayFromUrl === null) return;
    const n = parseInt(dayFromUrl, 10);
    if (Number.isInteger(n) && n >= 0 && n <= 14) {
      setDayModalOpen(n);
    }
  }, [dayFromUrl]);

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
    router.replace(url.pathname + "?" + url.searchParams.toString(), { scroll: false });
  };

  const closeDayModal = () => {
    setDayModalOpen(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("day");
    const q = url.searchParams.toString();
    router.replace(q ? url.pathname + "?" + q : url.pathname, { scroll: false });
  };

  const handleDayComplete = () => {
    setDayModalOpen(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("day");
    const q = url.searchParams.toString();
    router.replace(q ? url.pathname + "?" + q : url.pathname, { scroll: false });
    loadSprint();
    router.refresh();
  };

  const handleDayClick = (dayNumber: number) => {
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
    <div className="p-8 max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">Sprint Plan & Tracker</h1>
        <p className="text-muted-foreground mt-1">
          Your 14-day sprint mapped to a calendar. Click any sprint day to view details and take action.
        </p>
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
              Start a 14-day sprint to get your personalized plan with Build or Improve mode based on your business stage.
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
        >
          <SprintCalendar sprint={sprint} onDayClick={handleDayClick} />
        </motion.div>
      )}

      {dayModalOpen !== null && (
        <>
          {dayModalOpen === 0 && (
            <Day0Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDayComplete}
            />
          )}
          {dayModalOpen === 1 && (
            <Day1Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDayComplete}
            />
          )}
          {dayModalOpen === 2 && (
            <Day2Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDayComplete}
            />
          )}
          {dayModalOpen === 3 && (
            <Day3Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDayComplete}
            />
          )}
          {dayModalOpen >= 4 && dayModalOpen <= 14 && (
            <DayDetailModal
              packId={packId}
              dayNumber={dayModalOpen}
              open={true}
              onClose={closeDayModal}
              onComplete={handleDayComplete}
            />
          )}
        </>
      )}
    </div>
  );
}
