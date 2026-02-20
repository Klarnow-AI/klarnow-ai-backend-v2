"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Target,
  FileCode,
  Calendar,
  Image,
  Film,
  Users,
  FileCheck,
  Receipt,
  Shield,
  ChevronLeft,
} from "@/components/icons";
import { cn } from "@/lib/utils";

const packNav = [
  { href: "", label: "Overview", icon: LayoutDashboard },
  { href: "/brand-os", label: "Brand Identity", icon: Target },
  { href: "/website", label: "Website", icon: FileCode },
  { href: "/plan-tracker", label: "Plan & Tracker", icon: Calendar },
  { href: "/posters", label: "Posters & Flyers", icon: Image },
  { href: "/ad-factory", label: "Ad Factory", icon: Film },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/proposal", label: "Proposal", icon: FileCheck },
  { href: "/invoice", label: "Invoice", icon: Receipt },
  { href: "/proof-vault", label: "Proof Vault", icon: Shield },
];

export function PackSidebar() {
  const params = useParams();
  const pathname = usePathname();
  const packId = params.packId as string;
  const base = `/packs/${packId}`;

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-card/30 flex flex-col py-4">
      <Link
        href="/packs"
        className="mx-3 mb-2 flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      >
        <ChevronLeft className="h-4 w-4" />
        All packs
      </Link>
      <nav className="flex-1 px-2 space-y-0.5">
        {packNav.map((item) => {
          const href = `${base}${item.href}`;
          const isActive =
            pathname === href ||
            (item.href !== "" && pathname.startsWith(href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                isActive
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
