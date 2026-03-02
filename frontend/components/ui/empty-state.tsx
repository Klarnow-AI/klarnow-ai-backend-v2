"use client";

import { motion } from "framer-motion";
import { Plus } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";

export interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="border-dashed border-2 border-border/60 bg-card/30">
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-2xl bg-muted p-4 mb-4">{icon}</div>
          <CardTitle className="text-xl">{title}</CardTitle>
          <CardDescription className="mt-2 max-w-sm">{description}</CardDescription>
          {actionLabel && onAction && (
            <Button
              size="lg"
              className="gap-2 mt-6"
              onClick={onAction}
            >
              <Plus className="h-4 w-4" />
              {actionLabel}
            </Button>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
