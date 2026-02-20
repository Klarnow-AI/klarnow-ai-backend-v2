"use client";

import { createContext, useContext } from "react";

export type PackLayoutContextValue = {
  openChatPopover: () => void;
};

const PackLayoutContext = createContext<PackLayoutContextValue | null>(null);

export function PackLayoutProvider({
  children,
  value,
}: {
  children: React.ReactNode;
  value: PackLayoutContextValue;
}) {
  return (
    <PackLayoutContext.Provider value={value}>
      {children}
    </PackLayoutContext.Provider>
  );
}

export function usePackLayoutContext(): PackLayoutContextValue | null {
  return useContext(PackLayoutContext);
}
