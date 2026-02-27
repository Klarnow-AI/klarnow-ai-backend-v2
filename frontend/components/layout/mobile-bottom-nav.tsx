"use client";

import { MobileNavContent } from "./mobile-nav-content";

export function MobileBottomNav() {
  return (
    <div
      className="lg:hidden fixed bottom-0 left-0 right-0 z-30 px-2 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] pointer-events-none"
      aria-hidden={false}
    >
      <div className="mx-auto max-w-xs pointer-events-auto">
        <MobileNavContent inline={false} />
      </div>
    </div>
  );
}
