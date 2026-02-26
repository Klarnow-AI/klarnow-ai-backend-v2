"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Send } from "@/components/icons";
import { cn } from "@/lib/utils";

export type ParsedQuestion = {
  type: "select" | "text";
  text: string;
  options?: string[];
  placeholder?: string;
};

type QuestionFormProps = {
  questions: ParsedQuestion[];
  onSubmit: (answer: string) => void;
  disabled?: boolean;
};

export function QuestionForm({
  questions,
  onSubmit,
  disabled,
}: QuestionFormProps) {
  const [answers, setAnswers] = useState<Record<number, string | string[]>>(
    () => {
      const initial: Record<number, string | string[]> = {};
      questions.forEach((q, i) => {
        initial[i] = q.type === "select" ? [] : "";
      });
      return initial;
    },
  );

  const toggleOption = (qIndex: number, option: string) => {
    setAnswers((prev) => {
      const current = prev[qIndex] as string[];
      const next = current.includes(option)
        ? current.filter((o) => o !== option)
        : [...current, option];
      return { ...prev, [qIndex]: next };
    });
  };

  const setTextAnswer = (qIndex: number, value: string) => {
    setAnswers((prev) => ({ ...prev, [qIndex]: value }));
  };

  const hasAnyAnswer = Object.entries(answers).some(([, v]) =>
    Array.isArray(v)
      ? v.length > 0
      : typeof v === "string" && v.trim().length > 0,
  );

  const handleSubmit = () => {
    const parts: string[] = [];
    questions.forEach((q, i) => {
      const answer = answers[i];
      if (Array.isArray(answer) && answer.length > 0) {
        parts.push(`${q.text} ${answer.join(", ")}`);
      } else if (typeof answer === "string" && answer.trim()) {
        parts.push(`${q.text} ${answer.trim()}`);
      }
    });
    if (parts.length > 0) {
      onSubmit(parts.join("\n"));
    }
  };

  return (
    <div className="space-y-5">
      {questions.map((q, i) => (
        <div key={i} className="space-y-2">
          <p className="text-sm font-medium text-foreground">{q.text}</p>

          {q.type === "select" && q.options && (
            <div className="flex flex-wrap gap-1.5">
              {q.options.map((opt) => {
                const selected = (answers[i] as string[]).includes(opt);
                return (
                  <button
                    key={opt}
                    type="button"
                    disabled={disabled}
                    onClick={() => toggleOption(i, opt)}
                    className={cn(
                      "px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
                      selected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground",
                    )}
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
          )}

          {q.type === "text" && (
            <input
              type="text"
              disabled={disabled}
              placeholder={q.placeholder || "Type your answer…"}
              value={answers[i] as string}
              onChange={(e) => setTextAnswer(i, e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && hasAnyAnswer) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground transition-all focus:outline-none focus:scale-[1.02]"
            />
          )}
        </div>
      ))}

      <Button
        size="sm"
        disabled={!hasAnyAnswer || disabled}
        onClick={handleSubmit}
        className="gap-2"
      >
        <Send className="h-3.5 w-3.5" />
        Send answers
      </Button>
    </div>
  );
}
