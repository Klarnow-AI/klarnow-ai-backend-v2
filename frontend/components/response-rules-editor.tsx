"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  responseRulesApi,
  type ResponseRuleRead,
} from "@/api_requests/response-rules";

interface ResponseRulesEditorProps {
  packId: string;
  onLock?: () => void;
}

export function ResponseRulesEditor({
  packId,
  onLock,
}: ResponseRulesEditorProps) {
  const [rules, setRules] = useState<ResponseRuleRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [locking, setLocking] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refetch = () => {
    setLoading(true);
    setError(null);
    responseRulesApi
      .list(packId)
      .then(setRules)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load rules"),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refetch();
  }, [packId]);

  const handleGenerate = () => {
    setGenerating(true);
    setError(null);
    responseRulesApi
      .generate(packId)
      .then(setRules)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to generate"),
      )
      .finally(() => setGenerating(false));
  };

  const handleLock = () => {
    setLocking(true);
    setError(null);
    responseRulesApi
      .lock(packId)
      .then(setRules)
      .then(() => onLock?.())
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to lock"))
      .finally(() => setLocking(false));
  };

  const handleUpdateTemplate = (ruleId: string, response_template: string) => {
    const rule = rules.find((r) => r.id === ruleId);
    if (!rule || rule.locked_at) return;
    setSavingId(ruleId);
    responseRulesApi
      .update(ruleId, response_template)
      .then((updated) =>
        setRules((prev) => prev.map((r) => (r.id === ruleId ? updated : r))),
      )
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to save"))
      .finally(() => setSavingId(null));
  };

  const allLocked = rules.length > 0 && rules.every((r) => r.locked_at);

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="text-lg">Response rules</CardTitle>
        <p className="text-sm text-muted-foreground">
          Set templates for automated follow-up. Lock when ready (Step 8
          requirement).
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : rules.length === 0 ? (
          <div>
            <p className="text-sm text-muted-foreground mb-2">No rules yet.</p>
            <Button onClick={handleGenerate} disabled={generating}>
              {generating ? "Generating…" : "Generate default rules"}
            </Button>
          </div>
        ) : (
          <>
            <ul className="space-y-4">
              {rules.map((rule) => (
                <li key={rule.id} className="border rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium capitalize text-foreground">
                      {rule.trigger.replace(/_/g, " ")}
                    </span>
                    {rule.locked_at && (
                      <span className="text-xs text-muted-foreground">
                        Locked
                      </span>
                    )}
                  </div>
                  <textarea
                    className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
                    value={rule.response_template}
                    onChange={(e) =>
                      setRules((prev) =>
                        prev.map((r) =>
                          r.id === rule.id
                            ? { ...r, response_template: e.target.value }
                            : r,
                        ),
                      )
                    }
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v !== rule.response_template && !rule.locked_at) {
                        setRules((prev) =>
                          prev.map((r) =>
                            r.id === rule.id
                              ? { ...r, response_template: v }
                              : r,
                          ),
                        );
                        handleUpdateTemplate(rule.id, v);
                      }
                    }}
                    disabled={!!rule.locked_at}
                    placeholder="Response template…"
                  />
                  {savingId === rule.id && (
                    <span className="text-xs text-muted-foreground">
                      Saving…
                    </span>
                  )}
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              {!allLocked && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGenerate}
                  disabled={generating}
                >
                  {generating ? "Generating…" : "Regenerate rules"}
                </Button>
              )}
              {!allLocked && (
                <Button size="sm" onClick={handleLock} disabled={locking}>
                  {locking ? "Locking…" : "Lock rules (Step 8)"}
                </Button>
              )}
              {allLocked && (
                <span className="text-sm text-muted-foreground">
                  Rules are locked.
                </span>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
