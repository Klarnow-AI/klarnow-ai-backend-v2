"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogClose,
} from "@/components/ui/dialog";
import { Check, FileCheck, Sparkles, Target } from "@/components/icons";
import { getDayGuide } from "../_data/dayGuides";

interface DayGuideModalProps {
  dayNumber: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DayGuideModal({ dayNumber, open, onOpenChange }: DayGuideModalProps) {
  const guide = getDayGuide(dayNumber);
  const [checkedTasks, setCheckedTasks] = useState<Set<number>>(new Set());

  if (!guide) return null;

  const toggleTask = (index: number) => {
    const newChecked = new Set(checkedTasks);
    if (newChecked.has(index)) {
      newChecked.delete(index);
    } else {
      newChecked.add(index);
    }
    setCheckedTasks(newChecked);
  };

  const allTasksChecked = checkedTasks.size === guide.tasks.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-start justify-between gap-4 pr-8">
            <div>
              <DialogTitle>Day {dayNumber}: {guide.title}</DialogTitle>
              <DialogDescription>{guide.overview}</DialogDescription>
            </div>
          </div>
          <DialogClose onClose={() => onOpenChange(false)} />
        </DialogHeader>

        <DialogBody>
          <div className="space-y-6">
            {/* Tasks Section */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <FileCheck className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-foreground">Tasks</h3>
                {allTasksChecked && (
                  <span className="ml-auto text-xs text-green-600 dark:text-green-400 font-medium">
                    All complete!
                  </span>
                )}
              </div>
              <ul className="space-y-2">
                {guide.tasks.map((task, index) => {
                  const isChecked = checkedTasks.has(index);
                  return (
                    <li key={index} className="flex items-start gap-3 group">
                      <button
                        onClick={() => toggleTask(index)}
                        className="mt-0.5 flex-shrink-0"
                      >
                        <div
                          className={`h-5 w-5 rounded border-2 flex items-center justify-center transition-all ${
                            isChecked
                              ? "bg-primary border-primary"
                              : "border-muted-foreground/30 group-hover:border-primary/50"
                          }`}
                        >
                          {isChecked && <Check className="h-3 w-3 text-primary-foreground" />}
                        </div>
                      </button>
                      <span
                        className={`text-sm leading-relaxed ${
                          isChecked
                            ? "text-muted-foreground line-through"
                            : "text-foreground"
                        }`}
                      >
                        {task}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* Tips Section */}
            <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                <h3 className="font-semibold text-amber-900 dark:text-amber-100">Tips</h3>
              </div>
              <ul className="space-y-1.5">
                {guide.tips.map((tip, index) => (
                  <li key={index} className="text-sm text-amber-800 dark:text-amber-200 flex items-start gap-2">
                    <span className="text-amber-600 dark:text-amber-400 mt-0.5">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Expected Outcome Section */}
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900/30">
              <div className="flex items-center gap-2 mb-2">
                <Target className="h-5 w-5 text-green-600 dark:text-green-400" />
                <h3 className="font-semibold text-green-900 dark:text-green-100">Expected Outcome</h3>
              </div>
              <p className="text-sm text-green-800 dark:text-green-200">
                {guide.expectedOutcome}
              </p>
            </div>
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
