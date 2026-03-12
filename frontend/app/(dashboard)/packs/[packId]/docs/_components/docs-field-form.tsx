"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectItem } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import type { DocsTemplateField } from "@/types/api-types";
import { cn } from "@/lib/utils";

function fieldValueToString(value: unknown): string {
  if (value == null) return "";
  if (Array.isArray(value)) return value.map((item) => String(item)).join("\n");
  return String(value);
}

function parseFieldValue(field: DocsTemplateField, raw: string): unknown {
  if (field.input_type === "checklist") {
    return raw
      .split(/\n|,/)
      .map((part) => part.trim())
      .filter(Boolean);
  }
  return raw;
}

export function DocsFieldForm({
  fields,
  values,
  onChange,
  onPreset,
}: {
  fields: DocsTemplateField[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
  onPreset?: (key: string, value: string) => void;
}) {
  return (
    <div className="grid gap-4">
      {fields.map((field) => {
        const value = fieldValueToString(values[field.key]);
        const label = (
          <div className="flex items-center gap-2">
            <Label htmlFor={field.key} className="text-sm font-medium text-foreground">
              {field.label}
            </Label>
            {field.required && (
              <span className="rounded-md border border-border/60 bg-background px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Required
              </span>
            )}
          </div>
        );

        if (field.input_type === "dropdown") {
          return (
            <div
              key={field.key}
              className="grid gap-3 rounded-xl border border-border/50 bg-muted/10 px-4 py-4"
            >
              {label}
              <Select
                id={field.key}
                value={value}
                onChange={(event) => onChange(field.key, event.target.value)}
                className="docs-select"
              >
                <SelectItem value="">Select an option</SelectItem>
                {field.options.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </Select>
              {field.description && (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              )}
            </div>
          );
        }

        if (field.input_type === "radio" && field.options.length > 0) {
          return (
            <div
              key={field.key}
              className="grid gap-3 rounded-xl border border-border/50 bg-muted/10 px-4 py-4"
            >
              {label}
              <div className="flex flex-wrap gap-2">
                {field.options.map((option) => (
                  <Button
                    key={option}
                    type="button"
                    variant={value === option ? "default" : "outline"}
                    size="sm"
                    onClick={() => onChange(field.key, option)}
                    className={cn(
                      "h-8 px-3 text-xs",
                      value === option
                        ? "docs-button bg-foreground text-background hover:bg-foreground hover:text-background dark:hover:bg-foreground dark:hover:text-background"
                        : "docs-button-secondary h-8",
                    )}
                  >
                    {option}
                  </Button>
                ))}
              </div>
              {field.description && (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              )}
            </div>
          );
        }

        const isMultiline =
          field.input_type === "long_text" ||
          field.input_type === "notes" ||
          field.input_type === "checklist";

        return (
          <div
            key={field.key}
            className="grid gap-3 rounded-xl border border-border/50 bg-muted/10 px-4 py-4"
          >
            {label}
            {isMultiline ? (
              <Textarea
                id={field.key}
                value={value}
                rows={field.input_type === "notes" ? 8 : 5}
                className="docs-textarea"
                onChange={(event) =>
                  onChange(field.key, parseFieldValue(field, event.target.value))
                }
                placeholder={field.description || field.label}
              />
            ) : (
              <Input
                id={field.key}
                type={field.input_type === "date" ? "date" : "text"}
                value={value}
                className="docs-input"
                onChange={(event) =>
                  onChange(field.key, parseFieldValue(field, event.target.value))
                }
                placeholder={field.description || field.label}
              />
            )}
            {field.options.length > 0 && field.input_type === "checklist" && (
              <div className="flex flex-wrap gap-2">
                {field.options.map((option) => (
                  <Button
                    key={option}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => onPreset?.(field.key, option)}
                    className="docs-button-secondary h-8 px-3 text-xs"
                  >
                    {option}
                  </Button>
                ))}
              </div>
            )}
            {field.description && (
              <p className="text-xs text-muted-foreground">{field.description}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
