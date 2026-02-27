"use client";

import { useState, useCallback } from "react";
import { CreativeInput } from "../../_components/creative-input";

type AdFactoryInputBarProps = {
  packId: string;
  onOpenChat?: () => void;
  pendingChatKey: string;
};

export function AdFactoryInputBar({
  packId,
  onOpenChat,
  pendingChatKey,
}: AdFactoryInputBarProps) {
  const [input, setInput] = useState("");

  const handleSubmit = useCallback(
    (value: string) => {
      if (typeof window !== "undefined" && value.trim()) {
        try {
          sessionStorage.setItem(`${pendingChatKey}-${packId}`, value.trim());
        } catch {
          /* ignore */
        }
        onOpenChat?.();
      }
      setInput("");
    },
    [packId, onOpenChat, pendingChatKey],
  );

  return (
    <CreativeInput
      value={input}
      onChange={setInput}
      placeholder="Describe your video ad…"
      onSubmit={handleSubmit}
    />
  );
}
