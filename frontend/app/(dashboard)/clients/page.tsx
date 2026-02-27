"use client";

import { motion } from "framer-motion";
import { Users } from "@/components/icons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ClientsPage() {
  return (
    <div className="w-full max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl  font-[600] tracking-tight">Clients</h1>
        <p className="text-muted-foreground mt-1">
          Manage clients. Link to packs.
        </p>
      </motion.div>
      <Card asMotion delay={0.1}>
        <CardHeader className="flex flex-row items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-foreground">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <CardTitle>Clients</CardTitle>
            <CardDescription>
              CRUD at /api/v1/clients. Link via PATCH pack.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            List, create, update, delete. PATCH /api/v1/packs/{"{id}"} with
            client_id.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
