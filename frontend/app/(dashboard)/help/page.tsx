"use client";

import { motion } from "framer-motion";
import { HelpCircle } from "@/components/icons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function HelpPage() {
  return (
    <div className="p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">Help</h1>
        <p className="text-muted-foreground mt-1">Docs and support.</p>
      </motion.div>
      <Card asMotion delay={0.1}>
        <CardHeader className="flex flex-row items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
            <HelpCircle className="h-6 w-6" />
          </div>
          <div>
            <CardTitle>Help</CardTitle>
            <CardDescription>
              Klarnow AI — Campaign packs, Klaro, and governance.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            • Command Center: Chat with Klaro. Use Preview to see proposed
            changes, then Apply.
          </p>
          <p>
            • Packs: Create a pack, complete onboarding (max 6 questions), then
            explore Brand OS, Campaign, and more.
          </p>
          <p>
            • One CTA per campaign. No revenue guarantees in copy. Proof or
            waiver before publish/export.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
