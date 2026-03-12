"use client";

import Link from "next/link";
import { useParams, usePathname, useSearchParams } from "next/navigation";
import {
  Download,
  FileText,
  Layers,
  Plus,
  Receipt,
  Settings,
  Sparkles,
  Users,
} from "@/components/icons";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    href: "",
    label: "Home",
    description: "Suggestions, recents, and quick starts",
    icon: FileText,
  },
  {
    href: "/templates",
    label: "Templates",
    description: "Blueprints and section structures",
    icon: Layers,
  },
  {
    href: "/company-data",
    label: "Company Data",
    description: "Reusable business details and sign-off",
    icon: Users,
  },
  {
    href: "/exports",
    label: "Exports",
    description: "PDF downloads and invoice publishing",
    icon: Download,
  },
  {
    href: "/settings",
    label: "Settings",
    description: "Docs-specific defaults",
    icon: Settings,
  },
];

const CREATE_ITEMS = [
  {
    href: "?type=proposal&startMode=template",
    label: "Proposal",
    icon: Sparkles,
  },
  {
    href: "?type=invoice&startMode=template",
    label: "Invoice",
    icon: Receipt,
  },
  {
    href: "?type=meeting_summary&startMode=notes",
    label: "Meeting summary",
    icon: FileText,
  },
];

const TYPE_FILTERS = [
  "proposal",
  "invoice",
  "company_profile",
  "meeting_summary",
  "follow_up_summary",
  "employment_letter",
  "sponsorship_letter",
];

function formatLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getPageLabel(pathname: string, basePath: string): string {
  if (pathname === basePath) return "Home";
  if (pathname === `${basePath}/templates`) return "Templates";
  if (pathname === `${basePath}/company-data`) return "Company Data";
  if (pathname === `${basePath}/exports`) return "Exports";
  if (pathname === `${basePath}/settings`) return "Settings";
  if (pathname === `${basePath}/new`) return "New Document";
  return "Workspace";
}

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const packId = params.packId as string;
  const basePath = `/packs/${packId}/docs`;
  const typeFilter = searchParams.get("type");
  const pageLabel = getPageLabel(pathname, basePath);

  return (
    <div className="docs-shell">
      <aside className="docs-sidebar">
        <div className="docs-sidebar-section space-y-4">
          <div className="space-y-2 px-3">
            <p className="docs-eyebrow">Klarnow Docs</p>
            <div>
              <h1 className="text-lg font-semibold text-foreground">
                Pack documents
              </h1>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                One place for proposals, invoices, summaries, and formal
                letters.
              </p>
            </div>
          </div>
          <Link
            href={`${basePath}/new`}
            className="flex items-center justify-between rounded-lg border border-border/60 bg-background px-4 py-3 text-sm text-foreground transition-colors hover:bg-muted/20"
          >
            <span className="flex items-center gap-3">
              <Plus className="h-4 w-4" />
              New document
            </span>
            <span className="docs-chip">Guided</span>
          </Link>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="docs-sidebar-section space-y-1">
            <p className="docs-eyebrow px-3">Workspace</p>
            {NAV_ITEMS.map((item) => {
              const href = `${basePath}${item.href}`;
              const isActive = item.href
                ? pathname === href || pathname.startsWith(`${href}/`)
                : pathname === basePath;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href || "home"}
                  href={href}
                  className={cn(
                    "docs-sidebar-link",
                    isActive && "docs-sidebar-link-active",
                  )}
                >
                  <Icon className="mt-0.5 h-4 w-4" />
                  <span className="space-y-0.5">
                    <span className="block font-medium text-foreground">
                      {item.label}
                    </span>
                    <span className="block text-xs leading-5 text-muted-foreground">
                      {item.description}
                    </span>
                  </span>
                </Link>
              );
            })}
          </div>

          <div className="docs-sidebar-section space-y-1">
            <p className="docs-eyebrow px-3">Create</p>
            {CREATE_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.label}
                  href={`${basePath}/new${item.href}`}
                  className="docs-sidebar-link"
                >
                  <Icon className="mt-0.5 h-4 w-4" />
                  <span className="font-medium text-foreground">{item.label}</span>
                </Link>
              );
            })}
          </div>

          <div className="docs-sidebar-section space-y-1">
            <p className="docs-eyebrow px-3">Browse</p>
            {TYPE_FILTERS.map((type) => (
              <Link
                key={type}
                href={`${basePath}?type=${encodeURIComponent(type)}`}
                className={cn(
                  "docs-sidebar-link",
                  pathname === basePath && typeFilter === type && "docs-sidebar-link-active",
                )}
              >
                <FileText className="mt-0.5 h-4 w-4" />
                <span className="font-medium text-foreground">
                  {formatLabel(type)}
                </span>
              </Link>
            ))}
          </div>
        </div>

        <div className="docs-sidebar-section">
          <div className="docs-panel-muted px-3 py-3">
            <p className="docs-eyebrow">Defaults</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              PDF-first exports, pack-scoped context, and guided starts only.
            </p>
          </div>
        </div>
      </aside>

      <div className="docs-page">
        <div className="sticky top-0 z-20 border-b border-border/60 bg-background/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 md:px-8 lg:px-10">
            <div className="min-w-0">
              <p className="docs-eyebrow">Pack workspace</p>
              <div className="mt-1 flex items-center gap-2 text-sm">
                <Link
                  href={basePath}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Docs
                </Link>
                <span className="text-muted-foreground">/</span>
                <span className="truncate text-foreground">{pageLabel}</span>
              </div>
            </div>
            <Link
              href={`${basePath}/new`}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-foreground px-3 text-sm font-medium text-background transition-colors hover:bg-foreground/90"
            >
              <Plus className="h-4 w-4" />
              New
            </Link>
          </div>
          <div className="overflow-x-auto border-t border-border/50 lg:hidden">
            <div className="flex min-w-max gap-2 px-5 py-2">
              {NAV_ITEMS.map((item) => {
                const href = `${basePath}${item.href}`;
                const isActive = item.href
                  ? pathname === href || pathname.startsWith(`${href}/`)
                  : pathname === basePath;
                return (
                  <Link
                    key={item.href || "home-mobile"}
                    href={href}
                    className={cn(
                      "inline-flex items-center rounded-md px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-foreground text-background"
                        : "bg-muted/30 text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
