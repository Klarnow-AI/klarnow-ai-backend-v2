"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Check, Mail, Phone, Globe, MapPin, Palette, Pencil, Plus, Trash2 } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { ExtractBrandResponse } from "@/types/api-types";

interface BrandPreviewProps {
  data: ExtractBrandResponse;
  onConfirm: (finalData: ExtractBrandResponse) => void;
  onEdit?: () => void;
  onUploadLogo?: (file: File) => Promise<string | null>;
  loading?: boolean;
}

/** Deep copy ExtractBrandResponse so edits don't mutate parent. */
function copyExtractBrandResponse(data: ExtractBrandResponse): ExtractBrandResponse {
  return {
    brand_name: data.brand_name ?? "",
    offer_cues: Array.isArray(data.offer_cues) ? [...data.offer_cues] : [],
    tagline: data.tagline ?? null,
    description: data.description ?? null,
    industry: data.industry ?? null,
    contact_info: data.contact_info
      ? {
          email: data.contact_info.email ?? null,
          phone: data.contact_info.phone ?? null,
          address: data.contact_info.address ?? null,
        }
      : undefined,
    social_links: Array.isArray(data.social_links) ? [...data.social_links] : [],
    logo_url: data.logo_url ?? null,
    color_candidates: Array.isArray(data.color_candidates) ? [...data.color_candidates] : [],
    raw_extract: data.raw_extract ?? null,
  };
}

/** Normalize draft for confirm: trim scalars, filter empty array entries. */
function normalizeDraft(draft: ExtractBrandResponse): ExtractBrandResponse {
  return {
    ...draft,
    brand_name: (draft.brand_name ?? "").trim(),
    tagline: draft.tagline ? draft.tagline.trim() || null : null,
    description: draft.description ? draft.description.trim() || null : null,
    industry: draft.industry ? draft.industry.trim() || null : null,
    contact_info: draft.contact_info
      ? {
          email: draft.contact_info.email ? draft.contact_info.email.trim() || null : null,
          phone: draft.contact_info.phone ? draft.contact_info.phone.trim() || null : null,
          address: draft.contact_info.address ? draft.contact_info.address.trim() || null : null,
        }
      : undefined,
    offer_cues: (draft.offer_cues ?? []).map((s) => s.trim()).filter(Boolean),
    social_links: (draft.social_links ?? []).map((s) => s.trim()).filter(Boolean),
    color_candidates: (draft.color_candidates ?? []).map((s) => s.trim()).filter(Boolean),
    logo_url: draft.logo_url ? draft.logo_url.trim() || null : null,
  };
}

/**
 * Convert RGB color to hex code
 * Supports formats: rgb(255, 255, 255), rgba(255, 255, 255, 1), or hex colors
 */
function rgbToHex(color: string): string {
  if (color.startsWith("#")) return color;
  const rgbMatch = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)/);
  if (rgbMatch) {
    const r = parseInt(rgbMatch[1]);
    const g = parseInt(rgbMatch[2]);
    const b = parseInt(rgbMatch[3]);
    return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
  }
  return color;
}

/** Normalize to #rrggbb for input type="color" (expand 3-char hex if needed). */
function toPickerHex(color: string): string {
  const s = color?.trim();
  if (!s || !s.startsWith("#")) return "#000000";
  const hex = s.slice(1);
  if (/^[0-9a-fA-F]{6}$/.test(hex)) return s.toLowerCase();
  if (/^[0-9a-fA-F]{3}$/.test(hex)) {
    const r = hex[0] + hex[0];
    const g = hex[1] + hex[1];
    const b = hex[2] + hex[2];
    return `#${r}${g}${b}`.toLowerCase();
  }
  return "#000000";
}

export function BrandPreview({ data, onConfirm, onEdit, onUploadLogo, loading }: BrandPreviewProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ExtractBrandResponse>(() => copyExtractBrandResponse(data));
  const [logoUploading, setLogoUploading] = useState(false);
  const logoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDraft(copyExtractBrandResponse(data));
  }, [data]);

  const handleCancelEdit = useCallback(() => {
    setDraft(copyExtractBrandResponse(data));
    setEditing(false);
  }, [data]);

  const handleConfirm = useCallback(() => {
    onConfirm(normalizeDraft(draft));
  }, [draft, onConfirm]);

  const hasContactInfo =
    draft.contact_info &&
    (draft.contact_info.email || draft.contact_info.phone || draft.contact_info.address);
  const hasSocialLinks = draft.social_links && draft.social_links.length > 0;
  const hasColors = draft.color_candidates && draft.color_candidates.length > 0;

  if (editing) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-2xl mx-auto space-y-6"
      >
        <div className="text-center space-y-2">
          <h3 className="text-2xl font-semibold text-foreground">Edit extracted information</h3>
          <p className="text-sm text-muted-foreground">Update any field below, then confirm to continue</p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
          <div className="space-y-2">
            <Label htmlFor="brand_name">Brand name</Label>
            <Input
              id="brand_name"
              value={draft.brand_name ?? ""}
              onChange={(e) => setDraft((p) => ({ ...p, brand_name: e.target.value }))}
              placeholder="Brand name"
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tagline">Tagline (optional)</Label>
            <Input
              id="tagline"
              value={draft.tagline ?? ""}
              onChange={(e) => setDraft((p) => ({ ...p, tagline: e.target.value || null }))}
              placeholder="e.g. Your tagline"
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              value={draft.description ?? ""}
              onChange={(e) => setDraft((p) => ({ ...p, description: e.target.value || null }))}
              placeholder="Brand description"
              rows={3}
              disabled={loading}
              className="resize-none"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="industry">Industry (optional)</Label>
            <Input
              id="industry"
              value={draft.industry ?? ""}
              onChange={(e) => setDraft((p) => ({ ...p, industry: e.target.value || null }))}
              placeholder="e.g. Technology"
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="logo_url">Logo (optional)</Label>
            <div className="flex flex-col gap-2">
              {draft.logo_url && (
                <div className="flex items-center gap-3 p-2 rounded-lg bg-muted/50">
                  <img
                    src={draft.logo_url}
                    alt="Logo preview"
                    className="w-14 h-14 object-contain rounded border border-border"
                  />
                  <span className="text-xs text-muted-foreground truncate flex-1" title={draft.logo_url}>
                    {draft.logo_url}
                  </span>
                </div>
              )}
              <div className="flex gap-2 flex-wrap">
                {onUploadLogo && (
                  <>
                    <input
                      ref={logoInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      className="sr-only"
                      aria-hidden
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (!file || !onUploadLogo) return;
                        e.target.value = "";
                        setLogoUploading(true);
                        try {
                          const url = await onUploadLogo(file);
                          if (url) setDraft((p) => ({ ...p, logo_url: url }));
                        } finally {
                          setLogoUploading(false);
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={loading || logoUploading}
                      onClick={() => logoInputRef.current?.click()}
                      className="gap-1.5"
                    >
                      {logoUploading ? "Uploading…" : "Upload logo"}
                    </Button>
                  </>
                )}
                <Input
                  id="logo_url"
                  value={draft.logo_url ?? ""}
                  onChange={(e) => setDraft((p) => ({ ...p, logo_url: e.target.value || null }))}
                  placeholder="Or paste logo URL"
                  disabled={loading}
                  className="flex-1 min-w-[180px]"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-border space-y-3">
            <Label>Contact (optional)</Label>
            <div className="grid gap-3">
              <Input
                value={draft.contact_info?.email ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    contact_info: { ...p.contact_info, email: e.target.value || null },
                  }))
                }
                placeholder="Email"
                disabled={loading}
              />
              <Input
                value={draft.contact_info?.phone ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    contact_info: { ...p.contact_info, phone: e.target.value || null },
                  }))
                }
                placeholder="Phone"
                disabled={loading}
              />
              <Input
                value={draft.contact_info?.address ?? ""}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    contact_info: { ...p.contact_info, address: e.target.value || null },
                  }))
                }
                placeholder="Address"
                disabled={loading}
              />
            </div>
          </div>

          <div className="pt-4 border-t border-border space-y-2">
            <Label>Value propositions (one per line)</Label>
            <div className="space-y-2">
              {(draft.offer_cues?.length ? draft.offer_cues : [""]).map((cue, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={cue}
                    onChange={(e) => {
                      const next = [...(draft.offer_cues ?? [])];
                      next[idx] = e.target.value;
                      setDraft((p) => ({ ...p, offer_cues: next }));
                    }}
                    placeholder="Value proposition"
                    disabled={loading}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      const next = (draft.offer_cues ?? []).filter((_, i) => i !== idx);
                      setDraft((p) => ({ ...p, offer_cues: next.length ? next : [] }));
                    }}
                    disabled={loading}
                    aria-label="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDraft((p) => ({ ...p, offer_cues: [...(p.offer_cues ?? []), ""] }))}
                disabled={loading}
                className="gap-1.5"
              >
                <Plus className="h-4 w-4" />
                Add
              </Button>
            </div>
          </div>

          <div className="pt-4 border-t border-border space-y-2">
            <Label>Social links (one per line)</Label>
            <div className="space-y-2">
              {(draft.social_links?.length ? draft.social_links : [""]).map((link, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={link}
                    onChange={(e) => {
                      const next = [...(draft.social_links ?? [])];
                      next[idx] = e.target.value;
                      setDraft((p) => ({ ...p, social_links: next }));
                    }}
                    placeholder="https://..."
                    disabled={loading}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      const next = (draft.social_links ?? []).filter((_, i) => i !== idx);
                      setDraft((p) => ({ ...p, social_links: next.length ? next : [] }));
                    }}
                    disabled={loading}
                    aria-label="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDraft((p) => ({ ...p, social_links: [...(p.social_links ?? []), ""] }))}
                disabled={loading}
                className="gap-1.5"
              >
                <Plus className="h-4 w-4" />
                Add
              </Button>
            </div>
          </div>

          <div className="pt-4 border-t border-border space-y-2">
            <Label>Brand colors</Label>
            <div className="space-y-2">
              {(draft.color_candidates?.length ? draft.color_candidates : [""]).map((color, idx) => {
                const hex = color?.trim()
                  ? (color.startsWith("rgb") ? rgbToHex(color) : color.startsWith("#") ? color : `#${color}`)
                  : "#000000";
                const pickerValue = toPickerHex(hex);
                return (
                  <div key={idx} className="flex gap-2 items-center">
                    <input
                      type="color"
                      value={pickerValue}
                      onChange={(e) => {
                        const next = [...(draft.color_candidates ?? [])];
                        next[idx] = e.target.value;
                        setDraft((p) => ({ ...p, color_candidates: next }));
                      }}
                      disabled={loading}
                      className="w-10 h-10 rounded-lg border border-border cursor-pointer shrink-0 bg-transparent disabled:opacity-50 disabled:cursor-not-allowed [&::-webkit-color-swatch-wrapper]:p-0.5 [&::-webkit-color-swatch]:rounded [&::-webkit-color-swatch]:border-border"
                      aria-label={`Color ${idx + 1}`}
                    />
                    <span className="text-sm font-mono text-muted-foreground min-w-[72px]">
                      {pickerValue}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => {
                        const next = (draft.color_candidates ?? []).filter((_, i) => i !== idx);
                        setDraft((p) => ({ ...p, color_candidates: next.length ? next : [] }));
                      }}
                      disabled={loading}
                      aria-label="Remove color"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                );
              })}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setDraft((p) => ({ ...p, color_candidates: [...(p.color_candidates ?? []), "#000000"] }))
                }
                disabled={loading}
                className="gap-1.5"
              >
                <Plus className="h-4 w-4" />
                Add color
              </Button>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 justify-center">
          <Button variant="outline" onClick={handleCancelEdit} disabled={loading} className="min-w-[100px]">
            Cancel
          </Button>
          <Button variant="outline" onClick={() => setEditing(false)} disabled={loading} className="min-w-[100px]">
            Done
          </Button>
          <Button onClick={handleConfirm} disabled={loading} className="min-w-[120px]">
            {loading ? "Processing..." : "Looks Good"}
          </Button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-2xl mx-auto space-y-6"
    >
      <div className="text-center space-y-2">
        <h3 className="text-2xl font-semibold text-foreground">Here's what we found</h3>
        <p className="text-sm text-muted-foreground">Review the extracted information and confirm to continue</p>
      </div>

      <div className="bg-card border border-border rounded-2xl p-6 space-y-6">
        {draft.logo_url && (
          <div className="flex justify-center">
            <div className="w-24 h-24 rounded-xl overflow-hidden bg-muted flex items-center justify-center">
              <img
                src={draft.logo_url}
                alt={`${draft.brand_name} logo`}
                className="w-full h-full object-contain"
              />
            </div>
          </div>
        )}

        <div className="text-center">
          <h4 className="text-3xl font-bold text-foreground">{draft.brand_name}</h4>
          {draft.tagline && (
            <p className="mt-2 text-muted-foreground italic">&quot;{draft.tagline}&quot;</p>
          )}
        </div>

        {draft.description && (
          <div className="pt-4 border-t border-border">
            <p className="text-sm text-foreground/80 leading-relaxed">{draft.description}</p>
          </div>
        )}

        {draft.industry && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Industry:</span>
            <span className="font-medium text-foreground">{draft.industry}</span>
          </div>
        )}

        {draft.offer_cues && draft.offer_cues.length > 0 && (
          <div className="space-y-2">
            <h5 className="text-sm font-medium text-muted-foreground">Value Propositions</h5>
            <div className="flex flex-wrap gap-2">
              {draft.offer_cues.map((cue, idx) => (
                <div
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 text-primary rounded-full text-xs font-medium"
                >
                  <Check className="w-3 h-3" />
                  {cue}
                </div>
              ))}
            </div>
          </div>
        )}

        {hasContactInfo && (
          <div className="pt-4 border-t border-border space-y-3">
            <h5 className="text-sm font-medium text-muted-foreground">Contact Information</h5>
            <div className="grid gap-2">
              {draft.contact_info?.email && (
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="w-4 h-4 text-muted-foreground" />
                  <a
                    href={`mailto:${draft.contact_info.email}`}
                    className="text-foreground hover:text-primary transition-colors"
                  >
                    {draft.contact_info.email}
                  </a>
                </div>
              )}
              {draft.contact_info?.phone && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-muted-foreground" />
                  <a
                    href={`tel:${draft.contact_info.phone}`}
                    className="text-foreground hover:text-primary transition-colors"
                  >
                    {draft.contact_info.phone}
                  </a>
                </div>
              )}
              {draft.contact_info?.address && (
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="w-4 h-4 text-muted-foreground" />
                  <span className="text-foreground">{draft.contact_info.address}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {hasSocialLinks && (
          <div className="pt-4 border-t border-border space-y-3">
            <h5 className="text-sm font-medium text-muted-foreground">Social Media</h5>
            <div className="flex flex-wrap gap-2">
              {draft.social_links?.map((link, idx) => {
                try {
                  const domain = new URL(link).hostname.replace("www.", "");
                  return (
                    <a
                      key={idx}
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-lg text-xs font-medium transition-colors"
                    >
                      <Globe className="w-3 h-3" />
                      {domain}
                    </a>
                  );
                } catch {
                  return (
                    <span key={idx} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-muted rounded-lg text-xs">
                      {link}
                    </span>
                  );
                }
              })}
            </div>
          </div>
        )}

        {hasColors && (
          <div className="pt-4 border-t border-border space-y-3 pb-2">
            <h5 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Palette className="w-4 h-4" />
              Brand Colors
            </h5>
            <div className="flex flex-wrap gap-3 mb-6">
              {draft.color_candidates?.slice(0, 8).map((color, idx) => {
                const hexColor = rgbToHex(color);
                return (
                  <div key={idx} className="group relative flex flex-col items-center gap-1">
                    <div
                      className="w-12 h-12 rounded-lg border-2 border-border shadow-sm cursor-pointer transition-transform hover:scale-110"
                      style={{ backgroundColor: hexColor }}
                      title={hexColor}
                    />
                    <span className="absolute -bottom-6 text-xs text-muted-foreground font-mono opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap bg-background/90 px-2 py-1 rounded border border-border shadow-sm z-10">
                      {hexColor}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-3 justify-center">
        <Button
          variant="outline"
          onClick={() => setEditing(true)}
          disabled={loading}
          className="min-w-[120px] gap-1.5"
        >
          <Pencil className="h-4 w-4" />
          Edit Details
        </Button>
        <Button onClick={handleConfirm} disabled={loading} className="min-w-[120px]">
          {loading ? "Processing..." : "Looks Good"}
        </Button>
      </div>
    </motion.div>
  );
}
