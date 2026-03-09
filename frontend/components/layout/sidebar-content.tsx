"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useParams, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import {
  FolderKanban,
  PanelLeft,
  PanelRight,
  ChevronDown,
  LogOut,
  Lock,
  Plus,
  X,
} from "@/components/icons";
import { useDynamicPopover } from "@/hooks/use-dynamic-popover";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { PACKS_UPDATED_EVENT_NAME } from "@/contexts/new-pack-modal-context";
import { packs as packsApi, type Pack } from "@/lib/api";
import { ProfileAvatar } from "@/components/profile-avatar";
import { usePackGates } from "@/hooks/use-pack-gates";
import { buildItems, resultItems, navToSection } from "./nav-config";

const STORAGE_KEY_LAST_PACK = "sidebar-last-pack-id";

const SIDEBAR_WIDTH_EXPANDED = 256;
const SIDEBAR_WIDTH_COLLAPSED = 63;

const STORAGE_KEY_SIDEBAR = "sidebar-collapsed";

const navLinkClass = (isActive: boolean, collapsed?: boolean) =>
  cn(
    "flex items-center rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-0",
    collapsed ? "justify-center gap-0 px-2 py-2.5" : "gap-3 px-3 py-2.5",
    isActive
      ? "bg-muted/60 text-foreground"
      : "text-muted-foreground hover:text-foreground hover:bg-muted/40",
  );

export type SidebarContentProps = {
  variant: "desktop" | "sheet";
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  onClose?: () => void;
  onNavigate?: () => void;
};

export function SidebarContent({
  variant,
  collapsed = false,
  onToggleCollapsed,
  onClose,
  onNavigate,
}: SidebarContentProps) {
  const pathname = usePathname();
  const params = useParams();
  const urlPackId = params.packId as string | undefined;
  const { logout } = useAuth();
  const [packList, setPackList] = useState<Pack[]>([]);
  const [currentPack, setCurrentPack] = useState<Pack | null>(null);
  const [packDropdownOpen, setPackDropdownOpen] = useState(false);

  const {
    refs: packDropdownRefs,
    floatingStyles: packDropdownStyles,
    isPositioned: packDropdownPositioned,
  } = useDynamicPopover({
    open: packDropdownOpen,
    placement: "bottom-start",
  });

  const resolvedPackId =
    urlPackId ??
    (typeof window !== "undefined"
      ? localStorage.getItem(STORAGE_KEY_LAST_PACK)
      : null);
  const effectivePackId = urlPackId ?? resolvedPackId;
  const { gates } = usePackGates(effectivePackId || null);
  const router = useRouter();

  const { resolved: themeResolved } = useTheme();
  const logoSrc =
    themeResolved === "dark"
      ? "/logos/logo_white.svg"
      : "/logos/logo_black.svg";

  useEffect(() => {
    packsApi
      .list()
      .then((res) => setPackList(res.items))
      .catch(() => setPackList([]));
  }, []);

  useEffect(() => {
    function onPacksUpdated() {
      packsApi
        .list()
        .then((res) => setPackList(res.items))
        .catch(() => setPackList([]));
    }
    document.addEventListener(PACKS_UPDATED_EVENT_NAME, onPacksUpdated);
    return () =>
      document.removeEventListener(PACKS_UPDATED_EVENT_NAME, onPacksUpdated);
  }, []);

  useEffect(() => {
    if (urlPackId) {
      const fromList = packList.find((p) => p.id === urlPackId);
      if (fromList) {
        setCurrentPack(fromList);
        try {
          localStorage.setItem(STORAGE_KEY_LAST_PACK, urlPackId);
        } catch {}
        return;
      }
      packsApi
        .get(urlPackId)
        .then((p) => {
          setCurrentPack(p);
          try {
            localStorage.setItem(STORAGE_KEY_LAST_PACK, urlPackId);
          } catch {}
        })
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

  useEffect(() => {
    if (!packDropdownOpen) return;
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      const ref = packDropdownRefs.reference.current;
      if (
        (ref instanceof Element && ref.contains(target)) ||
        packDropdownRefs.floating.current?.contains(target)
      )
        return;
      setPackDropdownOpen(false);
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setPackDropdownOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [packDropdownOpen, packDropdownRefs.reference, packDropdownRefs.floating]);

  const packForLinks = effectivePackId ?? packList[0]?.id ?? null;
  const chatHref = packForLinks ? `/chat?pack=${packForLinks}` : "/chat";

  const buildHref = (pathSuffix: string): string => {
    if (pathSuffix === "/chat") return chatHref;
    if (!packForLinks) return "/packs";
    return `/packs/${packForLinks}${pathSuffix}`;
  };

  const resultHref = (pathSuffix: string): string => {
    if (pathSuffix === "/proposals")
      return packForLinks ? `/proposals?pack=${packForLinks}` : "/proposals";
    if (pathSuffix === "/invoices")
      return packForLinks ? `/invoices?pack=${packForLinks}` : "/invoices";
    if (!packForLinks) return "/packs";
    return `/packs/${packForLinks}${pathSuffix}`;
  };

  const isChatActive = pathname === "/chat" || pathname.startsWith("/chat?");
  const isProposalsActive =
    pathname === "/proposals" || pathname.startsWith("/proposals?");
  const isInvoicesActive =
    pathname === "/invoices" || pathname.startsWith("/invoices?");

  const handleLinkClick = () => {
    onNavigate?.();
  };

  const header = (
    <div
      className={cn(
        "flex items-center min-w-0 relative border-b border-border/40",
        variant === "sheet"
          ? "gap-2 p-4"
          : collapsed
            ? "justify-center p-2"
            : "gap-2 p-4",
      )}
    >
      {variant === "sheet" ? (
        <>
          <Link
            href="/chat"
            onClick={handleLinkClick}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden transition-all focus-visible:outline-none focus-visible:ring-0"
            title="Klarnow AI"
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
              className="flex min-w-0 flex-1 items-center gap-1 rounded-xl px-2 py-1.5 text-left transition-all focus-visible:outline-none focus-visible:ring-0"
              title={currentPack?.name ?? "Select a pack"}
            >
              <span className="min-w-0 flex-1 truncate text-right font-semibold text-lg text-foreground">
                {currentPack?.name ?? "Select a pack"}
              </span>
              <ChevronDown
                className={cn(
                  "h-5 w-5 shrink-0 transition-transform",
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
                        className="z-50 mt-1 w-[200px] max-h-64 overflow-y-auto rounded-2xl border-0 bg-border/40 backdrop-blur-2xl shadow shadow-black/5 dark:shadow-black/15 py-1"
                      >
                        {packList.map((pack) => (
                          <Link
                            key={pack.id}
                            href={`/packs/${pack.id}`}
                            onClick={() => {
                              setPackDropdownOpen(false);
                              handleLinkClick();
                              try {
                                localStorage.setItem(
                                  STORAGE_KEY_LAST_PACK,
                                  pack.id,
                                );
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
                              handleLinkClick();
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
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors"
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </>
      ) : collapsed ? (
        <div className="group relative flex h-9 w-9 shrink-0 cursor-pointer">
          <Link
            href="/chat"
            title="Home"
            className="flex h-full w-full items-center justify-center rounded-xl transition-all duration-150 group-hover:opacity-0 group-hover:pointer-events-none focus-visible:outline-none focus-visible:ring-0"
          >
            <Image
              src={logoSrc}
              alt="Klarnow AI"
              width={36}
              height={36}
              className="object-contain p-0.5"
            />
          </Link>
          <button
            type="button"
            onClick={onToggleCollapsed}
            title="Expand sidebar"
            className="absolute inset-0 flex items-center justify-center rounded-xl opacity-0 transition-all duration-150 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
          >
            <PanelRight className="h-5 w-5" />
          </button>
        </div>
      ) : (
        <>
          <div
            className="relative flex min-w-0 flex-1"
            ref={packDropdownRefs.setReference}
          >
            <Link
              href="/chat"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden transition-all focus-visible:outline-none focus-visible:ring-0"
              title="Klarnow AI"
            >
              <Image
                src={logoSrc}
                alt="Klarnow AI"
                width={36}
                height={36}
                className="object-contain p-0.5"
              />
            </Link>
            <button
              type="button"
              onClick={() => setPackDropdownOpen((o) => !o)}
              className="flex min-w-0 flex-1 items-center gap-1 rounded-xl px-2 py-1.5 text-left transition-all focus-visible:outline-none focus-visible:ring-0"
              title={currentPack?.name ?? "Select a pack"}
            >
              <span className="min-w-0 flex-1 truncate text-right font-semibold text-lg text-foreground">
                {currentPack?.name ?? "Select a pack"}
              </span>
              <ChevronDown
                className={cn(
                  "h-5 w-5 shrink-0 transition-transform",
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
                        className="z-50 mt-1 w-[200px] max-h-64 overflow-y-auto rounded-2xl border-0 bg-border/40 backdrop-blur-2xl shadow shadow-black/5 dark:shadow-black/15 py-1"
                      >
                        {packList.map((pack) => (
                          <Link
                            key={pack.id}
                            href={`/packs/${pack.id}`}
                            onClick={() => {
                              setPackDropdownOpen(false);
                              try {
                                localStorage.setItem(
                                  STORAGE_KEY_LAST_PACK,
                                  pack.id,
                                );
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
          {onToggleCollapsed && (
            <button
              type="button"
              onClick={onToggleCollapsed}
              title="Collapse sidebar"
              className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all"
            >
              <PanelLeft className="h-5 w-5" />
            </button>
          )}
        </>
      )}
    </div>
  );

  const isCollapsed = variant === "desktop" && collapsed;

  const renderNavLink = (
    item: {
      href: string;
      label: string;
      icon: React.ComponentType<{ className?: string }>;
      pathMatch: string;
      key?: string;
    },
    href: string,
    isActive: boolean,
    locked: boolean,
    lockedReason?: string | null,
  ) => {
    const Icon = item.icon;
    const gateReason =
      lockedReason?.trim() || `${item.label} is locked right now.`;
    if (locked) {
      return (
        <button
          type="button"
          key={item.key ?? item.href}
          onClick={() =>
            toast.error(`${item.label} is locked`, {
              description: gateReason,
            })
          }
          title={gateReason}
          aria-label={`${item.label}: ${gateReason}`}
          className={cn(
            "flex w-full items-center rounded-xl border-0 bg-transparent text-left text-sm font-medium cursor-not-allowed opacity-50 focus-visible:outline-none focus-visible:ring-0",
            isCollapsed
              ? "justify-center gap-0 px-2 py-2.5"
              : "gap-3 px-3 py-2.5",
            "text-muted-foreground",
          )}
        >
          <Lock className="h-5 w-5 shrink-0" />
          {!isCollapsed && item.label}
        </button>
      );
    }
    return (
      <Link
        key={item.key ?? item.href}
        href={href}
        onClick={handleLinkClick}
        className={navLinkClass(isActive, isCollapsed)}
        title={item.label}
      >
        <Icon className="h-5 w-5 shrink-0" />
        {!isCollapsed && item.label}
      </Link>
    );
  };

  return (
    <>
      {header}
      <nav className={cn("flex-1 overflow-y-auto", isCollapsed ? "p-2" : "p-3")}>
        <div className="space-y-1">
          {!isCollapsed && (
            <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
              Build
            </p>
          )}
          <div className="space-y-1">
            {buildItems.map((item) => {
              const isChat = item.pathMatch === "/chat";
              const isOverview = item.key === "overview";
              const href = isChat ? chatHref : buildHref(item.href);
              const isActive = isChat
                ? isChatActive
                : isOverview
                  ? effectivePackId
                    ? pathname === `/packs/${effectivePackId}`
                    : false
                  : effectivePackId
                    ? pathname === `/packs/${effectivePackId}${item.href}` ||
                      pathname.startsWith(
                        `/packs/${effectivePackId}${item.href}/`,
                      )
                    : false;
              const sectionKey = navToSection[item.href];
              const section =
                sectionKey && effectivePackId
                  ? gates?.sections[sectionKey]
                  : undefined;
              const locked = section ? !section.unlocked : false;
              return renderNavLink(
                item,
                href,
                isActive,
                locked,
                section?.reason,
              );
            })}
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-border/50 space-y-1">
          {!isCollapsed && (
            <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
              Result
            </p>
          )}
          <div className="space-y-1">
            {resultItems.map((item) => {
              const href =
                item.pathMatch === "/proposals"
                  ? packForLinks
                    ? `/proposals?pack=${packForLinks}`
                    : "/proposals"
                  : item.pathMatch === "/invoices"
                    ? packForLinks
                      ? `/invoices?pack=${packForLinks}`
                      : "/invoices"
                    : resultHref(item.href);
              const isActive =
                item.pathMatch === "/proposals"
                  ? isProposalsActive
                  : item.pathMatch === "/invoices"
                    ? isInvoicesActive
                    : effectivePackId
                      ? pathname === `/packs/${effectivePackId}${item.href}` ||
                        pathname.startsWith(
                          `/packs/${effectivePackId}${item.href}`,
                        )
                      : false;
              const sectionKey = navToSection[item.href];
              const section =
                sectionKey && effectivePackId
                  ? gates?.sections[sectionKey]
                  : undefined;
              const locked = section ? !section.unlocked : false;
              return renderNavLink(
                item,
                href,
                isActive,
                locked,
                section?.reason,
              );
            })}
          </div>
        </div>
      </nav>
      <div
        className={cn(
          "flex flex-col gap-0.5 shrink-0",
          isCollapsed ? "p-2 items-center" : "p-3",
        )}
      >
        <div className="mt-3 pt-3 border-t border-border/50 space-y-1 w-full">
          {!isCollapsed && (
            <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
              Account
            </p>
          )}
          <Link
            href="/settings"
            onClick={handleLinkClick}
            className={navLinkClass(pathname === "/settings", isCollapsed)}
            title="Account"
          >
            <ProfileAvatar className="h-5 w-5 shrink-0 rounded-full" />
            {!isCollapsed && <span className="truncate">Account</span>}
          </Link>
          <button
            type="button"
            onClick={() => void logout()}
            title="Sign out"
            className={cn(
              "flex items-center rounded-xl text-sm font-medium transition-all duration-200 w-full",
              isCollapsed
                ? "justify-center gap-0 px-2 py-2.5"
                : "gap-3 px-3 py-2.5",
              "text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
            )}
          >
            <LogOut className="h-5 w-5 shrink-0" />
            {!isCollapsed && <span>Sign out</span>}
          </button>
        </div>
      </div>
    </>
  );
}
