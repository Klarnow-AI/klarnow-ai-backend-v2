"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

const PACKS_UPDATED_EVENT = "packs-updated";

type NewPackModalContextValue = {
  open: boolean;
  openNewPackModal: () => void;
  closeNewPackModal: () => void;
};

const NewPackModalContext = createContext<NewPackModalContextValue | null>(
  null,
);

export function NewPackModalProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const openNewPackModal = useCallback(() => setOpen(true), []);
  const closeNewPackModal = useCallback(() => setOpen(false), []);

  const value: NewPackModalContextValue = {
    open,
    openNewPackModal,
    closeNewPackModal,
  };

  return (
    <NewPackModalContext.Provider value={value}>
      {children}
    </NewPackModalContext.Provider>
  );
}

export function useNewPackModal(): NewPackModalContextValue {
  const ctx = useContext(NewPackModalContext);
  if (!ctx) {
    throw new Error("useNewPackModal must be used within NewPackModalProvider");
  }
  return ctx;
}

/** Dispatch so sidebar (and others) can refetch pack list after a new pack is created. */
export function dispatchPacksUpdated() {
  if (typeof document !== "undefined") {
    document.dispatchEvent(new CustomEvent(PACKS_UPDATED_EVENT));
  }
}

export const PACKS_UPDATED_EVENT_NAME = PACKS_UPDATED_EVENT;
