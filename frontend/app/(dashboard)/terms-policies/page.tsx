"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { FileText } from "@/components/icons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function TermsPoliciesPage() {
  return (
    <div className="w-full max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-[600] tracking-tight">Terms & Policies</h1>
        <p className="text-muted-foreground mt-1">
          Legal terms, privacy details, and policy references.
        </p>
      </motion.div>

      <Card asMotion delay={0.1}>
        <CardHeader className="flex flex-row items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <CardTitle>Legal Documents</CardTitle>
            <CardDescription>
              Review our current legal and policy documents.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Read the full terms that apply to platform usage, billing, and
            account responsibilities.
          </p>
          <Link
            href="/terms"
            className="inline-flex rounded-lg px-1 py-0.5 text-foreground underline-offset-2 hover:underline"
          >
            View Terms of Service
          </Link>
          <p>
            Learn what information we collect, how it is used, and your data
            choices.
          </p>
          <Link
            href="/privacy"
            className="inline-flex rounded-lg px-1 py-0.5 text-foreground underline-offset-2 hover:underline"
          >
            View Privacy Policy
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
