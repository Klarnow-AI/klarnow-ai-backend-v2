"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Trash2, X } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { IconButton } from "@/components/ui/icon-button";
import type { Conversation } from "@/types/api-types";
import { buildChatUrl } from "../helpers";

export type ChatHistoryModalProps = {
  open: boolean;
  onClose: () => void;
  conversations: Conversation[];
  loading: boolean;
  packId: string | undefined;
  onDelete: (convId: string) => void;
  onSelectConversation?: (convId: string) => void;
};

export function ChatHistoryModal({
  open,
  onClose,
  conversations,
  loading,
  packId,
  onDelete,
  onSelectConversation,
}: ChatHistoryModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousFocusedElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocusedElementRef.current = document.activeElement as HTMLElement;

    const getFocusableElements = () => {
      if (!panelRef.current) return [] as HTMLElement[];
      return Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => el.offsetParent !== null);
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const focusable = getFocusableElements();
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    requestAnimationFrame(() => closeButtonRef.current?.focus());
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previousFocusedElementRef.current?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.2 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="history-modal-title"
          className="pointer-events-auto w-full max-w-md rounded-2xl border border-border bg-card shadow shadow-black/10 max-h-[80vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
          ref={panelRef}
        >
          <div className="relative p-4 border-b border-border">
            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              className="absolute right-3 top-3 p-1.5 rounded-lg text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            <h2
              id="history-modal-title"
              className="font-semibold text-lg text-foreground pr-10"
            >
              Chat history
            </h2>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto p-3">
            {loading ? (
              <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
                <Spinner className="h-5 w-5" />
                <span className="text-sm">Loading…</span>
              </div>
            ) : conversations.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No recent chats
              </p>
            ) : (
              <ul className="space-y-0.5">
                {conversations.map((conv) => (
                  <li
                    key={conv.id}
                    className="group flex items-center gap-1 rounded-xl hover:bg-muted"
                  >
                    {onSelectConversation ? (
                      <button
                        type="button"
                        onClick={() => {
                          onSelectConversation(conv.id);
                          onClose();
                        }}
                        className="min-w-0 flex-1 truncate px-3 py-2.5 text-left text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {conv.title || "Conversation"}
                      </button>
                    ) : (
                      <Link
                        href={buildChatUrl(conv.id, packId)}
                        onClick={onClose}
                        className="min-w-0 flex-1 truncate px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {conv.title || "Conversation"}
                      </Link>
                    )}
                    <IconButton
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label={`Delete ${conv.title || "conversation"}`}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onDelete(conv.id);
                      }}
                      className="shrink-0 opacity-60 hover:opacity-100 hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </IconButton>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </motion.div>
      </div>
    </>
  );
}
