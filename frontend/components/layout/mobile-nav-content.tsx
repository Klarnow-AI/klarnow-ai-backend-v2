"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Discover } from "@/components/icons";
import {
  buildItems,
  resultItems,
  footerItems,
  getNavItemByKey,
  type NavItem,
} from "./nav-config";
import { cn } from "@/lib/utils";

const STORAGE_KEY_LAST_PACK = "sidebar-last-pack-id";
const STORAGE_KEY_PINNED = "mobile-nav-pinned";

const FIXED_KEYS = ["chat", "plan-tracker"] as const;
const DEFAULT_PINNED = "posters";

function buildHref(item: NavItem, packId: string | null): string {
  if (item.key === "chat") {
    return packId ? `/chat?pack=${packId}` : "/chat";
  }
  if (item.global) {
    return item.href;
  }
  if (item.pathMatch === "/proposals") {
    return packId ? `/proposals?pack=${packId}` : "/proposals";
  }
  if (item.pathMatch === "/invoices") {
    return packId ? `/invoices?pack=${packId}` : "/invoices";
  }
  if (!packId) return "/packs";
  return `/packs/${packId}${item.pathMatch}`;
}

function isActive(
  pathname: string,
  item: NavItem,
  packId: string | null,
): boolean {
  if (item.key === "chat") {
    return pathname === "/chat" || pathname.startsWith("/chat?");
  }
  if (item.global) {
    return (
      pathname === item.pathMatch || pathname.startsWith(`${item.pathMatch}/`)
    );
  }
  if (item.pathMatch === "/proposals") {
    return pathname === "/proposals" || pathname.startsWith("/proposals?");
  }
  if (item.pathMatch === "/invoices") {
    return pathname === "/invoices" || pathname.startsWith("/invoices?");
  }
  if (!packId) return false;
  return (
    pathname === `/packs/${packId}${item.pathMatch}` ||
    pathname.startsWith(`/packs/${packId}${item.pathMatch}/`)
  );
}

function getDiscoverItems(pinnedKey: string): NavItem[] {
  const exclude = new Set<string>([...FIXED_KEYS, pinnedKey]);
  const all = [...buildItems, ...resultItems, ...footerItems];
  return all.filter((item) => !exclude.has(item.key));
}

export type MobileNavContentProps = {
  /** When true, renders in compact inline style for the input slot */
  inline?: boolean;
  className?: string;
};

export function MobileNavContent({ inline, className }: MobileNavContentProps) {
  const pathname = usePathname();
  const params = useParams();
  const urlPackId = params.packId as string | undefined;
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const discoverRef = useRef<HTMLDivElement>(null);

  const packId =
    urlPackId ??
    (typeof window !== "undefined"
      ? localStorage.getItem(STORAGE_KEY_LAST_PACK)
      : null);

  const [pinnedKey, setPinnedKey] = useState(DEFAULT_PINNED);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_PINNED);
      if (stored) setPinnedKey(stored);
    } catch {}
  }, []);

  const pinnedItem =
    getNavItemByKey(pinnedKey) ?? getNavItemByKey(DEFAULT_PINNED)!;
  const discoverItems = getDiscoverItems(pinnedKey);

  const handlePin = (key: string) => {
    setPinnedKey(key);
    try {
      localStorage.setItem(STORAGE_KEY_PINNED, key);
    } catch {}
    setDiscoverOpen(false);
  };

  useEffect(() => {
    if (!discoverOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (discoverRef.current?.contains(e.target as Node)) return;
      setDiscoverOpen(false);
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setDiscoverOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [discoverOpen]);

  useEffect(() => {
    setDiscoverOpen(false);
  }, [pathname]);

  const fixedItems: NavItem[] = [
    buildItems[0], // Chat
    buildItems[1], // Plan tracker
  ];

  const NavLink = ({ item }: { item: NavItem }) => {
    const href = buildHref(item, packId);
    const active = isActive(pathname, item, packId);
    const Icon = item.icon;
    return (
      <Link
        href={href}
        className={cn(
          "flex items-center justify-center flex-1 transition-colors rounded-full",
          active
            ? "text-primary"
            : "text-muted-foreground hover:text-foreground",
        )}
        aria-label={item.label}
        title={item.label}
      >
        <Icon className="h-6 w-6 shrink-0" />
      </Link>
    );
  };

  const navContent = (
    <div className="flex items-center flex-1">
      {fixedItems.map((item) => (
        <NavLink key={item.key} item={item} />
      ))}
      <NavLink item={pinnedItem} />
      <div
        className="relative flex items-center justify-center flex-1 min-w-0 py-1.5 px-0.5"
        ref={discoverRef}
      >
        <button
          type="button"
          onClick={() => setDiscoverOpen((o) => !o)}
          className={cn(
            "flex items-center justify-center rounded-full py-1.5 px-1 transition-colors",
            discoverOpen
              ? "text-primary bg-primary/10"
              : "text-muted-foreground hover:text-foreground",
          )}
          aria-label="Discover"
          aria-expanded={discoverOpen}
        >
          <Discover className="h-6 w-6 shrink-0" />
        </button>
        <AnimatePresence>
          {discoverOpen && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.15 }}
              className={cn(
                "fixed left-[0.5rem] right-[0.5rem] w-full max-w-[250px] mx-auto max-h-[min(70vh,calc(100dvh-6rem))] overflow-y-auto rounded-xl border border-border bg-card shadow-lg p-2 z-50 grid grid-cols-4 gap-1",
                inline
                  ? "bottom-[calc(5rem+env(safe-area-inset-bottom,0px))]"
                  : "bottom-[calc(5rem+env(safe-area-inset-bottom,0px))]",
              )}
            >
              {discoverItems.map((item) => {
                const Icon = item.icon;
                const href = buildHref(item, packId);
                return (
                  <Link
                    key={item.key}
                    href={href}
                    onClick={() => handlePin(item.key)}
                    aria-label={item.label}
                    title={item.label}
                    className="flex items-center justify-center p-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <Icon className="h-6 w-6 shrink-0" />
                  </Link>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );

  if (inline) {
    return (
      <div
        className={cn(
          "flex items-stretch w-full rounded-full border border-border bg-card/95 backdrop-blur-xl shadow-lg",
          className,
        )}
      >
        {navContent}
      </div>
    );
  }

  return (
    <nav
      className={cn(
        "mx-auto max-w-xs flex items-stretch h-[4.5rem] rounded-full border border-border bg-card/95 backdrop-blur-xl shadow-lg",
        className,
      )}
      aria-label="Bottom navigation"
    >
      {navContent}
    </nav>
  );
}
