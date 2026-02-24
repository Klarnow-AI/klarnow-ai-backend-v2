"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  FolderKanban,
  Users,
  HelpCircle,
  MenuCollapse,
  ChevronRight,
  ChevronDown,
  LogOut,
  Feedback,
  Target,
  FileCode,
  Calendar,
  Image as ImageIcon,
  Film,
  FileCheck,
  Receipt,
  Lock,
  Plus,
} from "@/components/icons";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { packs as packsApi, type Pack } from "@/lib/api";
import {
  subscriptionApi,
  type SubscriptionRead,
} from "@/api_requests/subscription";
import { ProfileAvatar } from "@/components/profile-avatar";
import { usePackGates } from "@/hooks/use-pack-gates";

const STORAGE_KEY_LAST_PACK = "sidebar-last-pack-id";

const buildItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare, pathMatch: "/chat" },
  {
    href: "/plan-tracker",
    label: "Plan and tracker",
    icon: Calendar,
    pathMatch: "/plan-tracker",
  },
  {
    href: "/brand-os",
    label: "Brand Identity",
    icon: Target,
    pathMatch: "/brand-os",
  },
  { href: "/website", label: "Website", icon: FileCode, pathMatch: "/website" },
  {
    href: "/posters",
    label: "Poster & flyer",
    icon: ImageIcon,
    pathMatch: "/posters",
  },
  {
    href: "/ad-factory",
    label: "Ad factory",
    icon: Film,
    pathMatch: "/ad-factory",
  },
];

const resultItems = [
  { href: "/leads", label: "Leads", icon: Users, pathMatch: "/leads" },
  {
    href: "/proposals",
    label: "Proposals",
    icon: FileCheck,
    pathMatch: "/proposals",
  },
  {
    href: "/invoices",
    label: "Invoices",
    icon: Receipt,
    pathMatch: "/invoices",
  },
];

const navToSection: Record<string, string> = {
  "/brand-os": "brand_os",
  "/website": "website",
  "/posters": "posters",
  "/ad-factory": "ad_factory",
  "/leads": "leads",
};

const SIDEBAR_WIDTH_EXPANDED = 280;
const SIDEBAR_WIDTH_COLLAPSED = 72;

const navLinkClass = (isActive: boolean, collapsed?: boolean) =>
  cn(
    "flex items-center rounded-xl text-sm font-medium transition-all duration-200",
    collapsed ? "justify-center gap-0 px-2 py-2.5" : "gap-3 px-3 py-2.5",
    isActive
      ? "font-semibold text-foreground bg-muted"
      : "text-muted-foreground hover:text-foreground hover:bg-muted",
  );

const STORAGE_KEY_SIDEBAR = "sidebar-collapsed";

export function Sidebar() {
  const pathname = usePathname();
  const params = useParams();
  const urlPackId = params.packId as string | undefined;
  const { logout } = useAuth();
  const [packList, setPackList] = useState<Pack[]>([]);
  const [currentPack, setCurrentPack] = useState<Pack | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionRead | null>(
    null,
  );
  const [packDropdownOpen, setPackDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_SIDEBAR);
      if (stored != null) setCollapsed(JSON.parse(stored));
    } catch {}
  }, []);

  const { resolved: themeResolved } = useTheme();
  const logoSrc =
    themeResolved === "dark"
      ? "/logos/logo_white.svg"
      : "/logos/logo_black.svg";

  const inPackDetail =
    pathname.startsWith("/packs/") && !!urlPackId && pathname !== "/packs";
  const resolvedPackId =
    urlPackId ??
    (typeof window !== "undefined"
      ? localStorage.getItem(STORAGE_KEY_LAST_PACK)
      : null);
  const effectivePackId = urlPackId ?? resolvedPackId;
  const { gates } = usePackGates(effectivePackId || null);

  useEffect(() => {
    packsApi
      .list()
      .then((res) => setPackList(res.items))
      .catch(() => setPackList([]));
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
      if (dropdownRef.current?.contains(e.target as Node)) return;
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
  }, [packDropdownOpen]);

  useEffect(() => {
    subscriptionApi
      .get()
      .then((s) => setSubscription(s))
      .catch(() => setSubscription(null));
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      const next = !c;
      try {
        localStorage.setItem(STORAGE_KEY_SIDEBAR, JSON.stringify(next));
      } catch {}
      return next;
    });
  };

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

  return (
    <motion.aside
      initial={{ width: 0, opacity: 0 }}
      animate={{
        width: collapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH_EXPANDED,
        opacity: 1,
      }}
      transition={{ duration: 0.25, ease: "easeInOut" }}
      className="shrink-0 m-10 rounded-2xl border border-border bg-card/95 backdrop-blur-2xl flex flex-col shadow shadow-black/5 dark:shadow-black/15 ring-1 ring-border/50 overflow-hidden"
    >
      <div
        className={cn(
          "border-b border-border flex items-center min-w-0 relative",
          collapsed ? "justify-center p-2" : "gap-2 p-4",
        )}
      >
        {collapsed ? (
          <div className="group relative flex h-9 w-9 shrink-0 cursor-pointer">
            <Link
              href="/chat"
              title="Home"
              className="flex h-full w-full items-center justify-center rounded-xl transition-opacity duration-150 group-hover:opacity-0 group-hover:pointer-events-none"
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
              onClick={toggleCollapsed}
              title="Expand sidebar"
              className="absolute inset-0 flex items-center justify-center rounded-xl opacity-0 transition-opacity duration-150 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        ) : (
          <>
            <div className="relative flex min-w-0 flex-1" ref={dropdownRef}>
              <Link
                href="/chat"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden"
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
                className="flex min-w-0 flex-1 items-center gap-2 rounded-xl px-2 py-1.5 text-left hover:bg-muted transition-colors"
                title={currentPack?.name ?? "Select a pack"}
              >
                <span className="min-w-0 truncate font-semibold text-lg text-foreground">
                  {currentPack?.name ?? "Select a pack"}
                </span>
                <ChevronDown
                  className={cn(
                    "h-5 w-5 shrink-0 transition-transform",
                    packDropdownOpen && "rotate-180",
                  )}
                />
              </button>
              <AnimatePresence>
                {packDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.15 }}
                    className="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-xl border border-border bg-card shadow-lg py-1"
                  >
                    {packList.map((pack) => (
                      <Link
                        key={pack.id}
                        href={`/packs/${pack.id}`}
                        onClick={() => setPackDropdownOpen(false)}
                        className={cn(
                          "flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors",
                          currentPack?.id === pack.id
                            ? "bg-muted text-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground",
                        )}
                      >
                        <FolderKanban className="h-4 w-4 shrink-0" />
                        <span className="truncate">{pack.name}</span>
                      </Link>
                    ))}
                    <div className="border-t border-border mt-1 pt-1">
                      <Link
                        href="/packs/new"
                        onClick={() => setPackDropdownOpen(false)}
                        className="flex items-center gap-2 px-3 py-2.5 text-sm font-medium text-primary hover:bg-muted"
                      >
                        <Plus className="h-4 w-4 shrink-0" />
                        New pack
                      </Link>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <button
              type="button"
              onClick={toggleCollapsed}
              title="Collapse sidebar"
              className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
            >
              <MenuCollapse className="h-5 w-5" />
            </button>
          </>
        )}
      </div>
      <nav
        className={cn(
          "flex-1 space-y-0.5 overflow-y-auto",
          collapsed ? "p-2" : "p-3",
        )}
      >
        {!collapsed && (
          <p className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Build
          </p>
        )}
        <div className="space-y-0.5">
          {buildItems.map((item) => {
            const isChat = item.pathMatch === "/chat";
            const href = isChat ? chatHref : buildHref(item.href);
            const isActive = isChat
              ? isChatActive
              : effectivePackId
                ? pathname === `/packs/${effectivePackId}${item.href}` ||
                  pathname.startsWith(`/packs/${effectivePackId}${item.href}/`)
                : false;
            const Icon = item.icon;
            const sectionKey = navToSection[item.href];
            const section =
              sectionKey && effectivePackId
                ? gates?.sections[sectionKey]
                : undefined;
            const locked = section ? !section.unlocked : false;

            if (locked) {
              return (
                <span
                  key={item.href}
                  className={cn(
                    "flex items-center rounded-xl text-sm font-medium transition-all duration-200 cursor-not-allowed opacity-50",
                    collapsed
                      ? "justify-center gap-0 px-2 py-2.5"
                      : "gap-3 px-3 py-2.5",
                    "text-muted-foreground",
                  )}
                  title={section?.reason ?? `${item.label} is locked`}
                >
                  <Lock className="h-5 w-5 shrink-0" />
                  {!collapsed && item.label}
                </span>
              );
            }
            return (
              <Link
                key={item.href}
                href={href}
                className={navLinkClass(isActive, collapsed)}
                title={item.label}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && item.label}
              </Link>
            );
          })}
        </div>

        {!collapsed && (
          <p className="px-3 py-1.5 pt-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Result
          </p>
        )}
        <div className="space-y-0.5">
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
            const Icon = item.icon;
            const sectionKey = navToSection[item.href];
            const section =
              sectionKey && effectivePackId
                ? gates?.sections[sectionKey]
                : undefined;
            const locked = section ? !section.unlocked : false;

            if (locked) {
              return (
                <span
                  key={item.href}
                  className={cn(
                    "flex items-center rounded-xl text-sm font-medium transition-all duration-200 cursor-not-allowed opacity-50",
                    collapsed
                      ? "justify-center gap-0 px-2 py-2.5"
                      : "gap-3 px-3 py-2.5",
                    "text-muted-foreground",
                  )}
                  title={section?.reason ?? `${item.label} is locked`}
                >
                  <Lock className="h-5 w-5 shrink-0" />
                  {!collapsed && item.label}
                </span>
              );
            }
            return (
              <Link
                key={item.href}
                href={href}
                className={navLinkClass(isActive, collapsed)}
                title={item.label}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && item.label}
              </Link>
            );
          })}
        </div>
      </nav>
      <div
        className={cn(
          "flex flex-col gap-0.5",
          collapsed ? "p-2 items-center" : "p-3",
        )}
      >
        {subscription && !collapsed && (
          <div className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-muted/50 text-sm">
            <span className="text-muted-foreground truncate">
              {subscription.credits_remaining} credits
            </span>
            <span className="shrink-0 font-medium capitalize text-foreground">
              {subscription.plan}
            </span>
          </div>
        )}
        {subscription && collapsed && (
          <div
            className="px-2 py-1.5 rounded-lg bg-muted/50 text-xs text-center text-muted-foreground"
            title={`${subscription.credits_remaining} credits · ${subscription.plan}`}
          >
            {subscription.credits_remaining}
          </div>
        )}
        <Link
          href="/feedback"
          className={navLinkClass(pathname === "/feedback", collapsed)}
          title="Feedback"
        >
          <Feedback className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Feedback</span>}
        </Link>
        <Link
          href="/help"
          className={navLinkClass(pathname === "/help", collapsed)}
          title="Help"
        >
          <HelpCircle className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Help</span>}
        </Link>
        <Link
          href="/settings"
          className={navLinkClass(pathname === "/settings", collapsed)}
          title="Account"
        >
          <ProfileAvatar className="h-5 w-5 shrink-0 rounded-full" />
          {!collapsed && <span className="truncate">Account</span>}
        </Link>
        <button
          type="button"
          onClick={() => logout()}
          title="Sign out"
          className={cn(
            "flex items-center rounded-xl text-sm font-medium transition-all duration-200 w-full",
            collapsed
              ? "justify-center gap-0 px-2 py-2.5"
              : "gap-3 px-3 py-2.5",
            "text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black",
          )}
        >
          <LogOut className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>
    </motion.aside>
  );
}
