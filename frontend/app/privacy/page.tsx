"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background/95 backdrop-blur-sm text-foreground max-w-2xl mx-auto">
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
        <h1 className="text-2xl  font-[600]">Privacy Policy</h1>
        <p className="text-muted-foreground text-sm">
          Privacy policy content. Placeholder for privacy policy.
        </p>
      </motion.div>
    </div>
  );
}
