"use client";

import { useMemo } from "react";
import { Clock, Search } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { SearchInput } from "@/components/ui/search-input";
import { DynamicPopover } from "@/components/ui/dynamic-popover";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/utils";
import type { Conversation } from "@/types/api-types";

type PackChatHistoryDropdownProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conversations: Conversation[];
  loading: boolean;
  activeConversationId: string | null;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onSelectConversation: (convId: string) => void;
  trigger?: React.ReactNode;
};

function formatRelativeTime(iso: string): string {
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return "";
  const now = Date.now();
  const diffMs = Math.max(0, now - time);
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diffMs < hour) return `${Math.max(1, Math.floor(diffMs / minute))}m`;
  if (diffMs < day) return `${Math.floor(diffMs / hour)}h`;
  return `${Math.floor(diffMs / day)}d`;
}

export function PackChatHistoryDropdown({
  open,
  onOpenChange,
  conversations,
  loading,
  activeConversationId,
  searchQuery,
  onSearchQueryChange,
  onSelectConversation,
  trigger,
}: PackChatHistoryDropdownProps) {
  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!normalizedQuery) return conversations;
    return conversations.filter((conv) => {
      const title = (conv.title || "").toLowerCase();
      return title.includes(normalizedQuery) || conv.id.includes(normalizedQuery);
    });
  }, [conversations, normalizedQuery]);

  return (
    <DynamicPopover
      open={open}
      onOpenChange={onOpenChange}
      placement="bottom-end"
      contentClassName="w-[min(26rem,88vw)] overflow-hidden"
      trigger={
        trigger ?? (
          <IconButton
            type="button"
            variant="ghost"
            size="sm"
            aria-label="Open chat history"
            className={cn(open ? "bg-muted text-foreground" : undefined)}
          >
            <Clock className="h-4 w-4" />
          </IconButton>
        )
      }
    >
      <div className="p-3 border-b border-border">
        <SearchInput
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          placeholder="Search recent tasks"
          className="text-sm"
          wrapperClassName="px-3 py-2.5"
          focusScale={false}
          leftAdornment={<Search className="h-4 w-4 text-muted-foreground" />}
          autoFocus
        />
      </div>
      <div className="max-h-[24rem] overflow-y-auto p-2">
        {loading ? (
          <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
            <Spinner className="h-5 w-5" />
            <span className="text-sm">Loading...</span>
          </div>
        ) : filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {conversations.length === 0 ? "No recent chats" : "No matching chats"}
          </p>
        ) : (
          <ul className="space-y-1">
            {filtered.map((conv) => {
              const active = conv.id === activeConversationId;
              const label = conv.title || "Conversation";
              return (
                <li key={conv.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onSelectConversation(conv.id);
                      onOpenChange(false);
                    }}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-left",
                      active
                        ? "bg-primary/20 text-foreground"
                        : "hover:bg-muted text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <span className="flex-1 min-w-0 truncate text-sm font-medium">
                      {label}
                    </span>
                    <span className="text-xs shrink-0 opacity-80">
                      {formatRelativeTime(conv.updated_at)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </DynamicPopover>
  );
}
