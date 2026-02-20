"use client";

import { motion } from "framer-motion";
import { Feedback } from "@/components/icons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function FeedbackPage() {
  return (
    <div className="p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">Feedback</h1>
        <p className="text-muted-foreground mt-1">
          Share your feedback and suggestions.
        </p>
      </motion.div>
      <Card asMotion delay={0.1}>
        <CardHeader className="flex flex-row items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
            <Feedback className="h-6 w-6" />
          </div>
          <div>
            <CardTitle>Feedback</CardTitle>
            <CardDescription>
              We’d love to hear from you. Share ideas, report issues, or suggest
              improvements.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>Feedback form and contact options can be added here.</p>
        </CardContent>
      </Card>
    </div>
  );
}
