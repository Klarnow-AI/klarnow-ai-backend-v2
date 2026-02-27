"use client";

import { MessageSquare } from "@/components/icons";
import { Button } from "@/components/ui/button";

export type ChatFabProps = {
  onNewChat: () => void;
};

export function ChatFab({ onNewChat }: ChatFabProps) {
  return (
    <Button
      type="button"
      variant="default"
      size="icon"
      onClick={onNewChat}
      aria-label="New chat"
      className="hidden md:flex fixed bottom-20 right-6 pb-safe pr-safe z-40 h-14 w-14 rounded-full shadow shadow-black/10 hover:shadow-md hover:shadow-black/15"
    >
      <MessageSquare className="h-6 w-6" />
    </Button>
  );
}
