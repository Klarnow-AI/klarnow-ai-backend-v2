"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "@/components/icons";
import { BrandPreview } from "@/components/ui/brand-preview";
import type { ExtractBrandResponse } from "@/types/api-types";

interface BrandPreviewModalProps {
  open: boolean;
  data: ExtractBrandResponse | null;
  onConfirm: () => void;
  onClose?: () => void;
  loading?: boolean;
}

export function BrandPreviewModal({ 
  open, 
  data, 
  onConfirm, 
  onClose,
  loading 
}: BrandPreviewModalProps) {
  if (!open || !data) return null;

  return (
    <AnimatePresence>
      {/* Darker backdrop z-[60] - on top of onboarding modal */}
      <motion.div
        key="brand-preview-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      
      {/* Preview modal z-[60] */}
      <div key="brand-preview-container" className="fixed inset-0 z-[60] flex items-center justify-center p-4 pointer-events-none">
        <motion.div
          key="brand-preview-modal"
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="brand-preview-title"
          className="pointer-events-auto w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl bg-background border border-border shadow-2xl relative"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 z-10 p-2 rounded-lg bg-background/80 backdrop-blur-sm text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Close preview"
            >
              <X className="w-5 h-5" />
            </button>
          )}
          
          {/* Preview content */}
          <div className="p-8">
            <BrandPreview
              data={data}
              onConfirm={onConfirm}
              loading={loading}
            />
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
