"use client";

import { motion } from "framer-motion";
import { Plus, FolderKanban } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";

export function PacksEmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="border-dashed border-2 border-border/60 bg-card/30">
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-2xl bg-muted p-4 mb-4">
            <FolderKanban className="h-12 w-12 text-muted-foreground" />
          </div>
          <CardTitle className="text-xl">No packs yet</CardTitle>
          <CardDescription className="mt-2 max-w-sm">
            Create your first campaign pack to get started. You&apos;ll answer a
            few questions, then Klaro will generate your Brand OS and Marketing
            Plan.
          </CardDescription>
          <Button size="lg" className="gap-2 mt-6" onClick={onCreate}>
            <Plus className="h-4 w-4" />
            Start new Campaign Pack
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  );
}
