"use client";

import { useState, useEffect } from "react";
import { Check } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { tasksApi, type FollowUpTaskRead } from "@/api_requests/tasks";

interface FollowUpQueueProps {
  packId: string;
  onTaskComplete?: () => void;
}

export function FollowUpQueue({ packId, onTaskComplete }: FollowUpQueueProps) {
  const [tasks, setTasks] = useState<FollowUpTaskRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [skippingId, setSkippingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    tasksApi
      .getPending(packId)
      .then(setTasks)
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [packId]);

  const handleCopy = (task: FollowUpTaskRead) => {
    navigator.clipboard.writeText(task.message_template);
    setCopiedId(task.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleComplete = async (taskId: string) => {
    setCompletingId(taskId);
    try {
      await tasksApi.complete(taskId);
      load();
      onTaskComplete?.();
    } finally {
      setCompletingId(null);
    }
  };

  const handleSkip = async (taskId: string) => {
    setSkippingId(taskId);
    try {
      await tasksApi.skip(taskId);
      load();
    } finally {
      setSkippingId(null);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Loading follow-ups…</p>
        </CardContent>
      </Card>
    );
  }

  if (tasks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Follow-up queue</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No pending follow-ups. New tasks appear when you add leads, send
            proposals, or send invoices.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          Follow-up queue ({tasks.length})
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Copy the message, send it externally, then mark done.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {tasks.map((task) => {
          const dueDate = new Date(task.due_date);
          const isOverdue = dueDate < new Date();
          const isDueToday =
            dueDate.toDateString() === new Date().toDateString();
          return (
          <div key={task.id} className="rounded-lg border p-3 space-y-2">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                {task.lead_name && (
                  <span className="text-sm font-medium">{task.lead_name}</span>
                )}
                <span className="text-xs font-medium text-muted-foreground uppercase">
                  {task.task_type.replace(/_/g, " ")}
                </span>
                {task.channel && (
                  <span className="text-xs text-muted-foreground">
                    via {task.channel}
                  </span>
                )}
              </div>
              <span
                className={`text-xs ${
                  isOverdue ? "text-destructive font-medium" : "text-muted-foreground"
                }`}
              >
                {isOverdue ? "Overdue" : isDueToday ? "Due today" : "Upcoming"} — {dueDate.toLocaleDateString()}
              </span>
            </div>
            {task.last_interaction_summary && (
              <p className="text-xs text-muted-foreground line-clamp-1">
                {task.last_interaction_summary}
              </p>
            )}
            <p className="text-sm line-clamp-2">{task.message_template}</p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopy(task)}
              >
                {copiedId === task.id ? <Check className="h-4 w-4" /> : null}
                {copiedId === task.id ? "Copied" : "Copy message"}
              </Button>
              <Button
                size="sm"
                onClick={() => handleComplete(task.id)}
                disabled={completingId === task.id}
              >
                {completingId === task.id ? "…" : "Mark done"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleSkip(task.id)}
                disabled={skippingId === task.id}
              >
                {skippingId === task.id ? "…" : "Skip"}
              </Button>
            </div>
          </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
