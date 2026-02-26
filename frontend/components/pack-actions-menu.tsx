"use client";

import { useState } from "react";
import { MoreVertical, Archive, RotateCcw, Trash2 } from "@/components/icons";
import { PackDeleteModal } from "@/components/pack-delete-modal";
import type { Pack } from "@/types/api-types";

type PackActionsMenuProps = {
  pack: Pack;
  onArchive: (packId: string) => Promise<void>;
  onRestore: (packId: string) => Promise<void>;
  onDelete: (packId: string) => Promise<void>;
};

export function PackActionsMenu({
  pack,
  onArchive,
  onRestore,
  onDelete,
}: PackActionsMenuProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<"archive" | "restore" | "delete">(
    "archive",
  );

  const isArchived = pack.status === "archived";

  function handleOpenModal(type: "archive" | "restore" | "delete") {
    setModalType(type);
    setModalOpen(true);
    setMenuOpen(false);
  }

  async function handleConfirm() {
    if (modalType === "archive") {
      await onArchive(pack.id);
    } else if (modalType === "restore") {
      await onRestore(pack.id);
    } else {
      await onDelete(pack.id);
    }
  }

  return (
    <>
      {/* Menu Button */}
      <div className="relative">
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setMenuOpen(!menuOpen);
          }}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          aria-label="Pack actions"
        >
          <MoreVertical className="h-4 w-4" />
        </button>

        {/* Dropdown Menu */}
        {menuOpen && (
          <>
            {/* Backdrop to close menu */}
            <div
              className="fixed inset-0 z-10"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setMenuOpen(false);
              }}
            />

            {/* Menu Items */}
            <div
              className="absolute left-0 mt-1 w-36 bg-background border border-border rounded-lg shadow-lg z-20 overflow-hidden"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
            >
              {isArchived ? (
                <>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleOpenModal("restore");
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                  >
                    <RotateCcw className="h-3.5 w-3.5 text-emerald-600" />
                    <span>Restore</span>
                  </button>
                  <div className="h-px bg-border" />
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleOpenModal("delete");
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Delete</span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleOpenModal("archive");
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                  >
                    <Archive className="h-3.5 w-3.5 text-amber-600" />
                    <span>Archive</span>
                  </button>
                  <div className="h-px bg-border" />
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleOpenModal("delete");
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Delete</span>
                  </button>
                </>
              )}
            </div>
          </>
        )}
      </div>

      {/* Confirmation Modal */}
      <PackDeleteModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        type={modalType}
        packName={pack.name}
        onConfirm={handleConfirm}
      />
    </>
  );
}
