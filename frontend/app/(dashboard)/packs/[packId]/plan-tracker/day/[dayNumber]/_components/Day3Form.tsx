"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

interface Day3FormProps {
  onSubmit: (selections: { hero_angle: string }) => Promise<void>;
  isSubmitting: boolean;
}

const HERO_ANGLES = [
  {
    value: "speed",
    label: "Speed",
    description: "Fast results, quick wins, rapid transformation",
  },
  {
    value: "quality",
    label: "Quality",
    description: "Premium results, excellence, best-in-class outcomes",
  },
  {
    value: "specialist",
    label: "Specialist",
    description: "Expert knowledge, niche authority, unique approach",
  },
  {
    value: "value",
    label: "Value",
    description: "Affordable, cost-effective, best ROI",
  },
];

export function Day3Form({ onSubmit, isSubmitting }: Day3FormProps) {
  const [heroAngle, setHeroAngle] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!heroAngle) return;
    await onSubmit({ hero_angle: heroAngle });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold">Day 3: Page Draft</h3>
          <p className="text-sm text-muted-foreground">
            Choose the hero angle that best represents your unique positioning.
            This will guide the AI in generating your landing page.
          </p>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="hero_angle">
              Hero Angle <span className="text-red-500">*</span>
            </Label>
            <Select
              id="hero_angle"
              value={heroAngle}
              onChange={(e) => setHeroAngle(e.target.value)}
              disabled={isSubmitting}
              required
            >
              <option value="">Select your hero angle</option>
              {HERO_ANGLES.map((angle) => (
                <option key={angle.value} value={angle.value}>
                  {angle.label} - {angle.description}
                </option>
              ))}
            </Select>
          </div>

          {heroAngle && (
            <div className="p-4 rounded-lg bg-muted/30">
              <p className="text-sm font-medium mb-1">
                {HERO_ANGLES.find((a) => a.value === heroAngle)?.label}
              </p>
              <p className="text-sm text-muted-foreground">
                {HERO_ANGLES.find((a) => a.value === heroAngle)?.description}
              </p>
            </div>
          )}
        </div>

        <div className="pt-4 border-t">
          <Button type="submit" disabled={!heroAngle || isSubmitting}>
            {isSubmitting ? "Completing Day 3..." : "Complete Day 3 & Generate Page"}
          </Button>
          {heroAngle && (
            <p className="text-xs text-muted-foreground mt-2">
              Completing Day 3 will automatically generate your website based on your selections.
            </p>
          )}
        </div>
      </div>
    </form>
  );
}
