"use client";

import {
  useFloating,
  offset,
  flip,
  shift,
  autoUpdate,
  type Placement,
} from "@floating-ui/react-dom";

export function useDynamicPopover(options?: {
  open?: boolean;
  placement?: Placement;
  offset?: number;
  padding?: number;
}) {
  const {
    open = true,
    placement = "bottom-start",
    offset: offsetValue = 8,
    padding = 8,
  } = options ?? {};

  const {
    refs,
    floatingStyles,
    placement: resolvedPlacement,
    isPositioned,
  } = useFloating({
    open,
    placement,
    strategy: "fixed",
    transform: false,
    middleware: [
      offset(offsetValue),
      flip({ padding }),
      shift({ padding }),
    ],
    whileElementsMounted: autoUpdate,
  });

  return {
    refs,
    floatingStyles,
    placement: resolvedPlacement,
    isPositioned: isPositioned ?? false,
  };
}
