"use client";

import Link from "next/link";
import Image from "next/image";
import { createPortal } from "react-dom";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, FolderKanban, Plus } from "@/components/icons";
import { useTheme } from "@/contexts/theme-context";
import { useDynamicPopover } from "@/hooks/use-dynamic-popover";
import { packs as packsApi, type Pack } from "@/lib/api";
import { PACKS_UPDATED_EVENT_NAME } from "@/contexts/new-pack-modal-context";
import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/page-loader";

const STORAGE_KEY_LAST_PACK = "sidebar-last-pack-id";

export function MobileHeaderBar() {
  const params = useParams();
  const router = useRouter();
  const urlPackId = params.packId as string | undefined;
  const [packList, setPackList] = useState<Pack[]>([]);
  const [currentPack, setCurrentPack] = useState<Pack | null>(null);
  const [packDropdownOpen, setPackDropdownOpen] = useState(false);
  const [packsLoading, setPacksLoading] = useState(true);
  const [packsError, setPacksError] = useState("");

  const {
    refs: packDropdownRefs,
    floatingStyles: packDropdownStyles,
    isPositioned: packDropdownPositioned,
  } = useDynamicPopover({
    open: packDropdownOpen,
    placement: "bottom-start",
  });

  const { resolved: themeResolved } = useTheme();
  const logoSrc =
    themeResolved === "dark"
      ? "/logos/logo_white.svg"
      : "/logos/logo_black.svg";

  const resolvedPackId =
    urlPackId ??
    (typeof window !== "undefined"
      ? localStorage.getItem(STORAGE_KEY_LAST_PACK)
      : null);

  const loadPackList = useCallback(async () => {
    setPacksLoading(true);
    setPacksError("");
    try {
      const res = await packsApi.list();
      setPackList(res.items);
    } catch {
      setPackList([]);
      setPacksError("Could not load packs.");
    } finally {
      setPacksLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPackList();
  }, [loadPackList]);

  useEffect(() => {
    function onPacksUpdated() {
      void loadPackList();
    }
    document.addEventListener(PACKS_UPDATED_EVENT_NAME, onPacksUpdated);
    return () =>
      document.removeEventListener(PACKS_UPDATED_EVENT_NAME, onPacksUpdated);
  }, [loadPackList]);

  useEffect(() => {
    if (urlPackId) {
      const fromList = packList.find((p) => p.id === urlPackId);
      if (fromList) {
        setCurrentPack(fromList);
        return;
      }
      packsApi
        .get(urlPackId)
        .then((p) => setCurrentPack(p))
        .catch(() => setCurrentPack(null));
    } else {
      if (resolvedPackId && packList.length > 0) {
        const fromList = packList.find((p) => p.id === resolvedPackId);
        setCurrentPack(fromList ?? null);
      } else {
        setCurrentPack(null);
      }
    }
  }, [urlPackId, resolvedPackId, packList]);

  return (
    <header className="shrink-0 flex items-center gap-3 px-4 py-3 bg-transparent">
      <Link
        href="/chat"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden"
        aria-label="Klarnow AI"
      >
        <Image
          src={logoSrc}
          alt="Klarnow AI"
          width={36}
          height={36}
          className="object-contain p-0.5"
        />
      </Link>
      <div
        className="relative flex min-w-0 flex-1"
        ref={packDropdownRefs.setReference}
      >
        <button
          type="button"
          onClick={() => setPackDropdownOpen((o) => !o)}
          className="flex min-w-0 flex-1 items-center gap-2 rounded-xl px-2 py-1.5 text-left transition-all focus-visible:outline-none focus-visible:ring-0"
          style={{ width: "250px" }}
          title={currentPack?.name ?? "Select a pack"}
        >
          <span className="min-w-0 flex-1 truncate text-sm font-semibold text-foreground">
            {currentPack?.name ?? "Select a pack"}
          </span>
          {packsLoading && <Spinner className="h-4 w-4 shrink-0" />}
          <ChevronDown
            className={cn(
              "h-5 w-5 shrink-0 text-muted-foreground transition-transform",
              packDropdownOpen && "rotate-180",
            )}
          />
        </button>
        {typeof document !== "undefined" &&
          createPortal(
            <AnimatePresence>
              {packDropdownOpen && (
                <div
                  ref={packDropdownRefs.setFloating}
                  style={{
                    ...packDropdownStyles,
                    zIndex: 90,
                  }}
                >
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="z-50 mt-1 w-[min(20rem,calc(100vw-2rem))] max-h-64 overflow-y-auto rounded-2xl border-0 bg-border/40 backdrop-blur-2xl shadow shadow-black/5 dark:shadow-black/15 py-1"
                  >
                    {packsError && (
                      <div className="px-3 py-2 text-xs text-destructive bg-border/20">
                        <p>{packsError}</p>
                        <button
                          type="button"
                          className="mt-1 underline"
                          onClick={() => void loadPackList()}
                        >
                          Retry
                        </button>
                      </div>
                    )}
                    {!packsLoading && packList.length === 0 && !packsError && (
                      <p className="px-3 py-2 text-sm text-muted-foreground">
                        No packs yet.
                      </p>
                    )}
                    {packList.map((pack) => (
                      <Link
                        key={pack.id}
                        href={`/chat?pack=${pack.id}`}
                        onClick={() => {
                          setPackDropdownOpen(false);
                          try {
                            localStorage.setItem(STORAGE_KEY_LAST_PACK, pack.id);
                          } catch {}
                        }}
                        className={cn(
                          "flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors",
                          currentPack?.id === pack.id
                            ? "bg-muted text-foreground"
                            : "text-muted-foreground hover:text-foreground",
                        )}
                      >
                        <FolderKanban className="h-4 w-4 shrink-0" />
                        <span className="truncate">{pack.name}</span>
                      </Link>
                    ))}
                  <div className="mt-1 pt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setPackDropdownOpen(false);
                        router.push("/packs/new");
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2.5 text-sm font-medium text-primary"
                    >
                      <Plus className="h-4 w-4 shrink-0" />
                      New pack
                    </button>
                  </div>
                </motion.div>
                </div>
              )}
            </AnimatePresence>,
            document.body,
          )}
      </div>
    </header>
  );
}
