"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, AlertCircle, Archive, RotateCcw, Trash2 } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ActionType = "archive" | "restore" | "delete";

type PackDeleteModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: ActionType;
  packName: string;
  onConfirm: () => Promise<void>;
};

const ACTION_CONFIG = {
  archive: {
    title: "Archive Pack",
    description:
      "This pack will be archived and hidden from your main list. You can restore it later.",
    confirmLabel: "Archive",
    confirmColor: "bg-amber-600 hover:bg-amber-700 text-white",
    icon: Archive,
    iconColor: "text-amber-600",
    requireTyping: false,
  },
  restore: {
    title: "Restore Pack",
    description:
      "This pack will be restored and moved back to your active packs list.",
    confirmLabel: "Restore",
    confirmColor: "bg-emerald-600 hover:bg-emerald-700 text-white",
    icon: RotateCcw,
    iconColor: "text-emerald-600",
    requireTyping: false,
  },
  delete: {
    title: "Delete Pack Permanently",
    description:
      "This action cannot be undone. All associated data will be permanently deleted:",
    confirmLabel: "Delete",
    confirmColor: "bg-red-600 hover:bg-red-700 text-white",
    icon: Trash2,
    iconColor: "text-red-600",
    requireTyping: true,
  },
};

const DELETED_DATA_LIST = [
  "Brand OS",
  "Campaigns",
  "Websites",
  "Plan Tracker",
  "Assets (images, videos, etc.)",
  "Proposals",
  "Invoices",
  "Proof Vault items",
];

export function PackDeleteModal({
  open,
  onOpenChange,
  type,
  packName,
  onConfirm,
}: PackDeleteModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [confirmText, setConfirmText] = useState("");

  const config = ACTION_CONFIG[type];
  const Icon = config.icon;
  const canConfirm = config.requireTyping ? confirmText === packName : true;

  useEffect(() => {
    if (open) {
      setConfirmText("");
      setError("");
      setLoading(false);
    }
  }, [open]);

  async function handleConfirm() {
    if (!canConfirm) return;

    setError("");
    setLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operation failed");
    } finally {
      setLoading(false);
    }
  }

  function handleClose() {
    if (!loading) {
      onOpenChange(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          />

          {/* Modal */}
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative w-full max-w-md bg-background border border-border rounded-2xl shadow-xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-start justify-between p-6 pb-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`p-2 rounded-full bg-muted ${config.iconColor}`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-foreground">
                      {config.title}
                    </h2>
                    <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                      {config.description}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClose}
                  disabled={loading}
                  className="text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Content */}
              <div className="px-6 pb-6">
                {/* Pack Name Display */}
                <div className="mb-4 p-3 bg-muted rounded-lg">
                  <p className="text-sm font-medium text-foreground">
                    {packName}
                  </p>
                </div>

                {/* Delete warning list */}
                {type === "delete" && (
                  <div className="mb-4 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-lg">
                    <div className="flex items-start gap-2 mb-2">
                      <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-500 mt-0.5 shrink-0" />
                      <p className="text-sm font-medium text-red-900 dark:text-red-100">
                        The following data will be permanently deleted:
                      </p>
                    </div>
                    <ul className="ml-6 space-y-1 text-sm text-red-800 dark:text-red-200">
                      {DELETED_DATA_LIST.map((item) => (
                        <li key={item} className="list-disc">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Type to confirm for delete */}
                {config.requireTyping && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Type <span className="font-semibold">{packName}</span> to
                      confirm
                    </label>
                    <Input
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          if (canConfirm) {
                            handleConfirm();
                          }
                        }
                      }}
                      placeholder={packName}
                      disabled={loading}
                      className="w-full"
                      autoComplete="off"
                    />
                  </div>
                )}

                {/* Error message */}
                {error && (
                  <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-lg">
                    <p className="text-sm text-red-900 dark:text-red-100">
                      {error}
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  <Button
                    onClick={handleClose}
                    disabled={loading}
                    variant="outline"
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleConfirm}
                    disabled={!canConfirm || loading}
                    className={`flex-1 ${config.confirmColor}`}
                  >
                    {loading ? "Processing..." : config.confirmLabel}
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
