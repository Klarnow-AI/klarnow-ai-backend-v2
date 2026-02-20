"use client";

import { motion } from "framer-motion";
import { FileCheck } from "@/components/icons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ProposalPage() {
  return (
    <div className="p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">Proposal</h1>
        <p className="text-muted-foreground mt-1">
          Draft, send, accept. Create via Chat or API.
        </p>
      </motion.div>
      <Card asMotion delay={0.1}>
        <CardHeader className="flex flex-row items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
            <FileCheck className="h-6 w-6" />
          </div>
          <div>
            <CardTitle>Proposal</CardTitle>
            <CardDescription>
              Revenue module. List/create/update from API.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            POST /api/v1/revenue/packs/{"{packId}"}/proposals
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
