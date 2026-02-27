"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground p-8 max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to Klarnow AI
        </Link>
        <h1 className="text-2xl  font-[600]">Terms of Service</h1>
        <p className="text-muted-foreground text-sm">
          Terms of service content. Placeholder for legal terms.
        </p>
      </motion.div>
    </div>
  );
}
