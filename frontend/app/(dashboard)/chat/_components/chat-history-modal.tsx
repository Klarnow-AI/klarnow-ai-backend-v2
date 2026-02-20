"use client";

import Link from "next/link";
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
};

export function ChatHistoryModal({
  open,
  onClose,
  conversations,
  loading,
  packId,
  onDelete,
}: ChatHistoryModalProps) {
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
        >
          <div className="relative p-4 border-b border-border">
            <button
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
                    <Link
                      href={buildChatUrl(conv.id, packId)}
                      onClick={onClose}
                      className="min-w-0 flex-1 truncate px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {conv.title || "Conversation"}
                    </Link>
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
