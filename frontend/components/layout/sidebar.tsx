"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { SidebarContent } from "./sidebar-content";

const STORAGE_KEY_SIDEBAR = "sidebar-collapsed";
const SIDEBAR_WIDTH_EXPANDED = 256;
const SIDEBAR_WIDTH_COLLAPSED = 63;

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_SIDEBAR);
      if (stored != null) setCollapsed(JSON.parse(stored));
    } catch {}
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
      className="hidden lg:flex shrink-0 m-4 rounded-2xl border border-border bg-card/95 backdrop-blur-2xl flex-col shadow shadow-black/5 dark:shadow-black/15 overflow-hidden"
    >
      <SidebarContent
        variant="desktop"
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
      />
    </motion.aside>
  );
}
