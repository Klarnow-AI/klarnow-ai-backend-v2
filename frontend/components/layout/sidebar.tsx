"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  FolderKanban,
  Palette,
  Users,
  Settings,
  HelpCircle,
  MenuCollapse,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Feedback,
  LayoutDashboard,
  Target,
  FileCode,
  Calendar,
  Image as ImageIcon,
  Film,
  FileCheck,
  Receipt,
  Lock,
} from "@/components/icons";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { packs as packsApi, type Pack } from "@/lib/api";
import { subscriptionApi, type SubscriptionRead } from "@/api_requests/subscription";
import { ProfileAvatar } from "@/components/profile-avatar";
import { usePackGates } from "@/hooks/use-pack-gates";

const navItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/packs", label: "Packs", icon: FolderKanban },
  { href: "/studio", label: "Studio", icon: Palette },
  { href: "/clients", label: "Clients", icon: Users },
  { href: "/proposals", label: "Proposals", icon: FileCheck },
  { href: "/invoices", label: "Invoices", icon: Receipt },
];

const packNavItems = [
  { href: "", label: "Overview", icon: LayoutDashboard },
  { href: "/plan-tracker", label: "Plan & Tracker", icon: Calendar },
  { href: "/brand-os", label: "Brand Identity", icon: Target },
  { href: "/website", label: "Website", icon: FileCode },
  { href: "/posters", label: "Posters & Flyers", icon: ImageIcon },
  { href: "/ad-factory", label: "Ad Factory", icon: Film },
  { href: "/leads", label: "Leads", icon: Users },
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

const itemVariants = {
  hidden: { opacity: 0, x: -12 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { duration: 0.25, ease: "easeOut", delay: 0.04 * i },
  }),
  exit: { opacity: 0, x: -8, transition: { duration: 0.15 } },
};

const listVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { delayChildren: 0.05 },
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.2 },
  },
};

const STORAGE_KEY_SIDEBAR = "sidebar-collapsed";

export function Sidebar() {
  const pathname = usePathname();
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string | undefined;
  const { logout } = useAuth();
  const [packList, setPackList] = useState<Pack[]>([]);
  const [currentPack, setCurrentPack] = useState<Pack | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionRead | null>(null);

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
      : "/logos/logo_color.svg";

  const inPackContext = pathname.startsWith("/packs");
  const onPacksList = pathname === "/packs";
  const onPackDetail = inPackContext && !!packId;
  const { gates } = usePackGates(onPackDetail ? packId : null);

  useEffect(() => {
    if (onPacksList) {
      packsApi
        .list()
        .then((res) => setPackList(res.items))
        .catch(() => setPackList([]));
    }
  }, [onPacksList]);

  useEffect(() => {
    if (onPackDetail && packId) {
      const fromList = packList.find((p) => p.id === packId);
      if (fromList) {
        setCurrentPack(fromList);
        return;
      }
      packsApi
        .get(packId)
        .then((p) => setCurrentPack(p))
        .catch(() => setCurrentPack(null));
    } else {
      setCurrentPack(null);
    }
  }, [onPackDetail, packId, packList]);

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
          "border-b border-border flex items-center min-w-0",
          collapsed ? "justify-center p-2" : "gap-2 p-4",
        )}
      >
        {collapsed ? (
          <div className="group relative flex h-9 w-9 shrink-0 cursor-pointer">
            <Link
              href="/"
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
            {!inPackContext ? (
              <Link
                href="/chat"
                className="flex min-w-0 flex-1 items-center gap-2"
                title="Klarnow AI"
              >
                <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden">
                  <Image
                    src={logoSrc}
                    alt="Klarnow AI"
                    width={36}
                    height={36}
                    className="object-contain p-0.5"
                  />
                </div>
                <span className="min-w-0 truncate font-semibold text-lg text-foreground">
                  Klarnow AI
                </span>
              </Link>
            ) : onPacksList ? (
              <Link
                href="/chat"
                className="flex min-w-0 flex-1 items-center gap-2"
                title="Packs"
              >
                <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden">
                  <Image
                    src={logoSrc}
                    alt="Klarnow AI"
                    width={36}
                    height={36}
                    className="object-contain p-0.5"
                  />
                </div>
                <span className="min-w-0 truncate font-semibold text-lg text-foreground">
                  Packs
                </span>
              </Link>
            ) : (
              <div
                className="flex min-w-0 flex-1 items-center gap-2"
                title={currentPack?.name ?? "Pack"}
              >
                <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden">
                  <Image
                    src={logoSrc}
                    alt="Klarnow AI"
                    width={36}
                    height={36}
                    className="object-contain p-0.5"
                  />
                </div>
                <span className="min-w-0 truncate font-semibold text-lg text-foreground">
                  {currentPack?.name ?? "Pack"}
                </span>
                {/* {currentPack && (
                  <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
                    <PackActionsMenu
                      pack={currentPack}
                      onArchive={handleArchive}
                      onRestore={handleRestore}
                      onDelete={handleDelete}
                    />
                  </div>
                )} */}
              </div>
            )}
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
        <AnimatePresence mode="wait">
          {inPackContext ? (
            <motion.div
              key="pack"
              variants={listVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="space-y-0.5"
            >
              <motion.div variants={itemVariants} custom={1}>
                <Link
                  href={onPacksList ? "/chat" : "/packs"}
                  className={navLinkClass(false, collapsed)}
                  title={onPacksList ? "Back" : "All packs"}
                >
                  <ChevronLeft className="h-5 w-5 shrink-0" />
                  {!collapsed && (onPacksList ? "Back" : "All packs")}
                </Link>
              </motion.div>
              {onPacksList && (
                <div className="mt-2 space-y-0.5">
                  {packList.map((pack, i) => (
                    <motion.div
                      key={pack.id}
                      variants={itemVariants}
                      custom={i + 2}
                      initial="hidden"
                      animate="visible"
                    >
                      <Link
                        href={`/packs/${pack.id}`}
                        className={navLinkClass(
                          pathname === `/packs/${pack.id}`,
                          collapsed,
                        )}
                        title={pack.name}
                      >
                        <FolderKanban className="h-5 w-5 shrink-0" />
                        {!collapsed && (
                          <span className="truncate">{pack.name}</span>
                        )}
                      </Link>
                    </motion.div>
                  ))}
                </div>
              )}
              {onPackDetail && packId && (
                <div className="mt-2 space-y-0.5">
                  {packNavItems.map((item, i) => {
                    const href = `/packs/${packId}${item.href}`;
                    const isActive =
                      pathname === href ||
                      (item.href !== "" && pathname.startsWith(href));
                    const Icon = item.icon;
                    const sectionKey = navToSection[item.href];
                    const section = sectionKey ? gates?.sections[sectionKey] : undefined;
                    const locked = section ? !section.unlocked : false;

                    return (
                      <motion.div
                        key={item.href || "overview"}
                        variants={itemVariants}
                        custom={i + 2}
                        initial="hidden"
                        animate="visible"
                      >
                        {locked ? (
                          <span
                            className={cn(
                              "flex items-center rounded-xl text-sm font-medium transition-all duration-200 cursor-not-allowed opacity-50",
                              collapsed ? "justify-center gap-0 px-2 py-2.5" : "gap-3 px-3 py-2.5",
                              "text-muted-foreground",
                            )}
                            title={section?.reason ?? `${item.label} is locked`}
                          >
                            <Lock className="h-5 w-5 shrink-0" />
                            {!collapsed && item.label}
                          </span>
                        ) : (
                          <Link
                            href={href}
                            className={navLinkClass(isActive, collapsed)}
                            title={item.label}
                          >
                            <Icon className="h-5 w-5 shrink-0" />
                            {!collapsed && item.label}
                          </Link>
                        )}
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="main"
              variants={listVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="space-y-0.5"
            >
              {navItems.map((item, i) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <motion.div
                    key={item.href}
                    variants={itemVariants}
                    custom={i + 1}
                    initial="hidden"
                    animate="visible"
                  >
                    <Link
                      href={item.href}
                      className={navLinkClass(isActive, collapsed)}
                      title={item.label}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      {!collapsed && item.label}
                    </Link>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
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
          <div className="px-2 py-1.5 rounded-lg bg-muted/50 text-xs text-center text-muted-foreground" title={`${subscription.credits_remaining} credits · ${subscription.plan}`}>
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
