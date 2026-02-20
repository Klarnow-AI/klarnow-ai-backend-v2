"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Spinner } from "@/components/ui/page-loader";
import { packs as packsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function NewPackPage() {
  const [name, setName] = useState("My Campaign Pack");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const pack = await packsApi.create(name);
      router.push(`/packs/${pack.id}/onboarding`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create pack");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-lg mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold tracking-tight">New Campaign Pack</h1>
        <p className="text-muted-foreground mt-1">
          Give your pack a name. Next you&apos;ll answer a few questions for
          Klaro.
        </p>
      </motion.div>
      <Card asMotion delay={0.1}>
        <form onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle>Pack name</CardTitle>
            <CardDescription>You can change this later.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <p className="text-sm text-muted-foreground bg-white/10 rounded-lg px-3 py-2 border border-border">
                {error}
              </p>
            )}
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Campaign Pack"
              required
            />
          </CardContent>
          <CardFooter className="gap-3">
            <Button type="submit" disabled={loading}>
              {loading ? (
                <Spinner className="h-4 w-4" />
              ) : (
                "Create and continue"
              )}
            </Button>
            <Button type="button" variant="ghost" onClick={() => router.back()}>
              Cancel
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
