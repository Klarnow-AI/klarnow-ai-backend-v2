"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type MobileSidebarContextValue = {
  isOpen: boolean;
  setOpen: (open: boolean) => void;
  open: () => void;
  close: () => void;
  toggle: () => void;
};

const MobileSidebarContext = createContext<MobileSidebarContextValue | null>(
  null,
);

export function MobileSidebarProvider({ children }: { children: ReactNode }) {
  const [isOpen, setOpen] = useState(false);

  const open = useCallback(() => setOpen(true), []);
  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  const value = useMemo(
    () => ({
      isOpen,
      setOpen,
      open,
      close,
      toggle,
    }),
    [isOpen, open, close, toggle],
  );

  return (
    <MobileSidebarContext.Provider value={value}>
      {children}
    </MobileSidebarContext.Provider>
  );
}

export function useMobileSidebar() {
  const ctx = useContext(MobileSidebarContext);
  if (!ctx) {
    return {
      isOpen: false,
      setOpen: () => {},
      open: () => {},
      close: () => {},
      toggle: () => {},
    };
  }
  return ctx;
}
