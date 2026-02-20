"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface Day2FormProps {
  onSubmit: (selections: { primary_pain: string; primary_outcome: string }) => Promise<void>;
  isSubmitting: boolean;
}

export function Day2Form({ onSubmit, isSubmitting }: Day2FormProps) {
  const [pain, setPain] = useState("");
  const [outcome, setOutcome] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pain.trim() || !outcome.trim()) return;
    await onSubmit({
      primary_pain: pain.trim(),
      primary_outcome: outcome.trim(),
    });
  };

  const isValid = pain.trim().length > 0 && outcome.trim().length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold">Day 2: Audience Lock</h3>
          <p className="text-sm text-muted-foreground">
            Define the primary pain point your audience faces and the outcome they desire.
          </p>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="primary_pain">
              Primary Pain Point <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="primary_pain"
              value={pain}
              onChange={(e) => setPain(e.target.value)}
              placeholder="What is the main problem or frustration your target audience experiences?"
              rows={4}
              required
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              Example: "Struggling to generate consistent leads for their business"
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="primary_outcome">
              Primary Outcome <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="primary_outcome"
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
              placeholder="What is the desired result or transformation they want to achieve?"
              rows={4}
              required
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              Example: "A steady stream of qualified leads without paid ads"
            </p>
          </div>
        </div>

        <div className="pt-4 border-t">
          <Button type="submit" disabled={!isValid || isSubmitting}>
            {isSubmitting ? "Completing Day 2..." : "Complete Day 2"}
          </Button>
        </div>
      </div>
    </form>
  );
}
