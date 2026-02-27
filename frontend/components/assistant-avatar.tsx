"use client";

import { useState, useEffect } from "react";
import Lottie from "lottie-react";
import { Bot } from "@/components/icons";
import { cn } from "@/lib/utils";

let cachedAnimationData: object | null = null;

async function loadAnimationData(): Promise<object | null> {
  if (cachedAnimationData) return cachedAnimationData;
  try {
    const res = await fetch("/assets/jsons/assistant-avatar.json");
    if (!res.ok) return null;
    const data = await res.json();
    cachedAnimationData = data;
    return data;
  } catch {
    return null;
  }
}

export function AssistantAvatar({ className }: { className?: string }) {
  const [animationData, setAnimationData] = useState<object | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    loadAnimationData()
      .then((data) => {
        setAnimationData(data);
        if (!data) setError(true);
      })
      .catch(() => setError(true));
  }, []);

  const sizeClasses = "h-12 w-12 shrink-0";

  if (error || !animationData) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-full bg-muted text-muted-foreground",
          sizeClasses,
          className,
        )}
        aria-hidden
      >
        <Bot className="h-4 w-4" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center overflow-hidden",
        sizeClasses,
        className,
      )}
      aria-hidden
    >
      <Lottie
        animationData={animationData}
        loop
        autoplay
        className="h-full w-full"
      />
    </div>
  );
}
