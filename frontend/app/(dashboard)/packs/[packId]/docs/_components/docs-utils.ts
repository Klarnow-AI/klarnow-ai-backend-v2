import type { DocsDocumentType } from "@/types/api-types";

export function formatDocTypeLabel(type: DocsDocumentType | string): string {
  return type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function listToTextarea(value: unknown[] | null | undefined): string {
  if (!value || value.length === 0) return "";
  return value.map((item) => String(item)).join("\n");
}

export function textareaToList(value: string): string[] {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}
