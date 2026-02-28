"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const base =
  "text-sm [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:my-2 [&_ol]:my-2 [&_li]:ml-4 [&_ul]:list-disc [&_ol]:list-decimal [&_pre]:my-2 [&_pre]:p-3 [&_pre]:rounded-lg [&_pre]:bg-black/5 dark:[&_pre]:bg-white/10 [&_pre]:overflow-x-auto [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:bg-black/5 dark:[&_code]:bg-white/10 [&_code]:text-sm [&_pre_code]:p-0 [&_pre_code]:bg-transparent [&_strong]:font-semibold [&_a]:underline [&_a]:underline-offset-2 [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-sm [&_h1]: font-[600] [&_h2]: font-[600] [&_h3]:font-semibold [&_h1]:mt-2 [&_h2]:mt-2 [&_h3]:mt-1.5 [&_h1]:mb-1 [&_h2]:mb-1 [&_h3]:mb-1";

export interface MarkdownContentProps {
  children: string;
  className?: string;
}

export function MarkdownContent({ children, className }: MarkdownContentProps) {
  return (
    <div className={cn(base, className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
