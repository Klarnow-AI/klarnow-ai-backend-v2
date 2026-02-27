"use client";

import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";

type MobileInputNavContextValue = {
  showNavInsteadOfInput: boolean;
  setShowNavInsteadOfInput: (value: boolean) => void;
  hasInputOnPage: boolean;
  setHasInputOnPage: (value: boolean) => void;
};

const MobileInputNavContext = createContext<MobileInputNavContextValue | null>(
  null,
);

export function MobileInputNavProvider({ children }: { children: ReactNode }) {
  const [showNavInsteadOfInput, setShowNavInsteadOfInput] = useState(false);
  const [hasInputOnPage, setHasInputOnPage] = useState(false);

  return (
    <MobileInputNavContext.Provider
      value={{
        showNavInsteadOfInput,
        setShowNavInsteadOfInput,
        hasInputOnPage,
        setHasInputOnPage,
      }}
    >
      {children}
    </MobileInputNavContext.Provider>
  );
}

export function useMobileInputNav() {
  const ctx = useContext(MobileInputNavContext);
  if (!ctx) {
    return {
      showNavInsteadOfInput: false,
      setShowNavInsteadOfInput: () => {},
      hasInputOnPage: false,
      setHasInputOnPage: () => {},
    };
  }
  return ctx;
}
