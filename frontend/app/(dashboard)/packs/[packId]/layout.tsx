"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { createPortal } from "react-dom";
import { usePathname, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare } from "@/components/icons";
import { useIsTabletOrLarger } from "@/hooks/use-media-query";
import { Sheet, SheetContent } from "@/components/ui/sheet";
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
  const [chatOpen, setChatOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const fabRef = useRef<HTMLButtonElement>(null);
  const isTabletOrLarger = useIsTabletOrLarger();

  const isPackOverview = !!packId && pathname === `/packs/${packId}`;
  const showFab = !!packId && !isPackOverview;

  const layoutContextValue = useMemo(
    () => ({ openChatPopover: () => setChatOpen(true) }),
    [],
  );

  useEffect(() => {
    if (!chatOpen || !isTabletOrLarger) return;
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      if (
        popoverRef.current?.contains(target) ||
        fabRef.current?.contains(target)
      )
        return;
      setChatOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [chatOpen, isTabletOrLarger]);

  useEffect(() => {
    if (!chatOpen) return;
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setChatOpen(false);
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [chatOpen]);

  return (
    <PackLayoutProvider value={layoutContextValue}>
      <div className="flex-1 flex flex-col min-h-0 min-w-0 overflow-y-auto overflow-x-hidden">
        {children}
      </div>
      {showFab && packId && (
        <>
          <button
            ref={fabRef}
            type="button"
            onClick={() => setChatOpen((open) => !open)}
            aria-label="Chat with Klaro"
            className="hidden md:flex fixed bottom-6 right-6 pb-safe pr-safe z-40 h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-black/10 transition-all hover:shadow-xl hover:shadow-black/15 hover:scale-105 focus:outline-none focus:scale-105"
          >
            <MessageSquare className="h-6 w-6" />
          </button>
          {isTabletOrLarger &&
            typeof document !== "undefined" &&
            createPortal(
              <AnimatePresence>
                {chatOpen && (
                  <motion.div
                    key="pack-chat-popover"
                    ref={popoverRef}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    transition={{ duration: 0.15 }}
                    className="fixed right-6 bottom-24 z-50 flex h-[70vh] max-h-[80vh] w-[380px] max-w-[calc(100vw-3rem)] flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-lg"
                  >
                    <div className="flex min-h-0 flex-1 flex-col">
                      <PackChatPanel packId={packId} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>,
              document.body,
            )}
          {!isTabletOrLarger && (
            <Sheet open={chatOpen} onOpenChange={setChatOpen} side="right">
              <SheetContent className="p-0">
                <PackChatPanel packId={packId} />
              </SheetContent>
            </Sheet>
          )}
        </>
      )}
    </PackLayoutProvider>
  );
}
