import type { ComponentType } from "react";
import {
  MessageSquare,
  LayoutDashboard,
  Target,
  FileCode,
  Image as ImageIcon,
  Film,
  Users,
  FileText,
  Settings,
} from "@/components/icons";

export type NavItem = {
  key: string;
  href: string;
  label: string;
  icon: ComponentType<{ className?: string; size?: number }>;
  pathMatch: string;
  /** Pack-scoped: href is appended to /packs/{packId} */
  packScoped?: boolean;
  /** Global: href is used as-is (e.g. /feedback, /help, /settings) */
  global?: boolean;
};

export const buildItems: NavItem[] = [
  {
    key: "overview",
    href: "",
    label: "Overview",
    icon: LayoutDashboard,
    pathMatch: "",
    packScoped: true,
  },
  { key: "chat", href: "/chat", label: "Chat", icon: MessageSquare, pathMatch: "/chat" },
  {
    key: "brand-os",
    href: "/brand-os",
    label: "Brand Identity",
    icon: Target,
    pathMatch: "/brand-os",
    packScoped: true,
  },
  {
    key: "website",
    href: "/website",
    label: "Website",
    icon: FileCode,
    pathMatch: "/website",
    packScoped: true,
  },
  {
    key: "posters",
    href: "/posters",
    label: "Poster & flyer",
    icon: ImageIcon,
    pathMatch: "/posters",
    packScoped: true,
  },
  {
    key: "ad-factory",
    href: "/ad-factory",
    label: "Ad factory",
    icon: Film,
    pathMatch: "/ad-factory",
    packScoped: true,
  },
];

export const resultItems: NavItem[] = [
  { key: "leads", href: "/leads", label: "Leads", icon: Users, pathMatch: "/leads", packScoped: true },
  {
    key: "docs",
    href: "/docs",
    label: "Docs",
    icon: FileText,
    pathMatch: "/docs",
    packScoped: true,
  },
];

export const footerItems: NavItem[] = [
  { key: "settings", href: "/settings", label: "Account", icon: Settings, pathMatch: "/settings", global: true },
];

export const navToSection: Record<string, string> = {
  "/brand-os": "brand_os",
  "/website": "website",
  "/posters": "posters",
  "/ad-factory": "ad_factory",
  "/leads": "leads",
};

/** All nav items (build + result + footer) for use in More popover */
export function getAllNavItems(): NavItem[] {
  return [...buildItems, ...resultItems, ...footerItems];
}

/** Get item by key */
export function getNavItemByKey(key: string): NavItem | undefined {
  return getAllNavItems().find((item) => item.key === key);
}
