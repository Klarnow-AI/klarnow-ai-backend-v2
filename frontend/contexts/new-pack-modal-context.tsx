const PACKS_UPDATED_EVENT = "packs-updated";

/** Dispatch so sidebar (and others) can refetch pack list after a new pack is created. */
export function dispatchPacksUpdated() {
  if (typeof document !== "undefined") {
    document.dispatchEvent(new CustomEvent(PACKS_UPDATED_EVENT));
  }
}

export const PACKS_UPDATED_EVENT_NAME = PACKS_UPDATED_EVENT;
