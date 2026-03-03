"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { FolderPlus } from "@/components/icons";
import { PageLoader } from "@/components/ui/page-loader";
import { useAuth } from "@/contexts/auth-context";
import { useLandingContext } from "@/hooks/use-landing-context";
import { ComposeInput } from "@/components/ui/compose-input";
import { Chip } from "@/components/ui/chip";
import { AuthModal } from "@/components/auth-modal";
import { PublicHeader } from "@/components/public-header";

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const { context, isLoading: landingLoading } = useLandingContext();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [authModalOpen, setAuthModalOpen] = useState(false);

  useEffect(() => {
    if (isLoading || !isAuthenticated) return;
    if (landingLoading) return;
    if (context?.pack?.id) {
      router.replace(`/packs/${context.pack.id}`);
      return;
    }
    router.replace("/packs/new");
  }, [isAuthenticated, isLoading, landingLoading, context, router]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setAuthModalOpen(true);
  };

  function handleDashboardClick(e: React.MouseEvent) {
    e.preventDefault();
    setAuthModalOpen(true);
  }

  function handleRegisterSuccess() {
    setAuthModalOpen(false);
    router.push("/packs/new");
  }

  if (isLoading || isAuthenticated) {
    return <PageLoader variant="screen" message="Loading…" />;
  }

  return (
    <div className="relative min-h-screen flex flex-col text-foreground overflow-hidden bg-background">
      <AuthModal
        open={authModalOpen}
        onOpenChange={setAuthModalOpen}
        onRegisterSuccess={handleRegisterSuccess}
      />
      <PublicHeader
        onDashboardClick={handleDashboardClick}
        onAuthClick={() => setAuthModalOpen(true)}
        showInstallAbout
      />

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="w-full max-w-4xl flex flex-col items-center text-center px-4 sm:px-6"
        >
          <h3 className="font-heading font-[500] text-foreground tracking-tight mb-2 line-clamp-2 text-3xl sm:text-4xl md:text-5xl leading-tight">
            Build a business people come back to.
          </h3>
          <p className="text-muted-foreground text-md">
            A 14-day sprint that helps you publish, capture leads, and get paid.
          </p>
          <div className="mb-10" />

          {/* Main input */}
          <ComposeInput
            value={query}
            onChange={setQuery}
            onSubmit={handleSubmit}
            placeholder="Describe the campaign you want to launch…"
            wrapperClassName="mb-2"
          />

          <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              <Chip
                size="md"
                icon={<FolderPlus />}
                onClick={() => setAuthModalOpen(true)}
              >
                Create Campaign Pack
              </Chip>
            </motion.div>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
