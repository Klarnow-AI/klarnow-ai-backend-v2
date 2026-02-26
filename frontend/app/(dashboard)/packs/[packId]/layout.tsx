"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { createPortal } from "react-dom";
import { usePathname, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare } from "@/components/icons";
import { PackLayoutProvider } from "./_context/pack-layout-context";
import { PackChatPanel } from "./_components/pack-chat-panel";

export default function PackLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const params = useParams();
  const packId = params.packId as string | undefined;
  const [chatPopoverOpen, setChatPopoverOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const fabRef = useRef<HTMLButtonElement>(null);

  const isPackOverview = !!packId && pathname === `/packs/${packId}`;
  const showFab = !!packId && !isPackOverview;

  const layoutContextValue = useMemo(
    () => ({ openChatPopover: () => setChatPopoverOpen(true) }),
    [],
  );

  useEffect(() => {
    if (!chatPopoverOpen) return;
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      if (
        popoverRef.current?.contains(target) ||
        fabRef.current?.contains(target)
      )
        return;
      setChatPopoverOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [chatPopoverOpen]);

  useEffect(() => {
    if (!chatPopoverOpen) return;
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setChatPopoverOpen(false);
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [chatPopoverOpen]);

  return (
    <PackLayoutProvider value={layoutContextValue}>
      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
        {children}
      </div>
      {showFab && (
        <>
          <button
            ref={fabRef}
            type="button"
            onClick={() => setChatPopoverOpen((open) => !open)}
            aria-label="Chat with Klaro"
            className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-black/10 transition-all hover:shadow-xl hover:shadow-black/15 hover:scale-105 focus:outline-none focus:scale-105"
          >
            <MessageSquare className="h-6 w-6" />
          </button>
          {typeof document !== "undefined" &&
            createPortal(
              <AnimatePresence>
                {chatPopoverOpen && (
                  <motion.div
                    key="pack-chat-popover"
                    ref={popoverRef}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    transition={{ duration: 0.15 }}
                    className="fixed right-6 bottom-24 z-50 flex h-[70vh] max-h-[80vh] w-[380px] flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-lg"
                  >
                    <div className="flex min-h-0 flex-1 flex-col">
                      <PackChatPanel packId={packId} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>,
              document.body,
            )}
        </>
      )}
    </PackLayoutProvider>
  );
}
