"use client";

import { motion } from "framer-motion";
import { Check, Mail, Phone, Globe, MapPin, Palette } from "@/components/icons";
import { Button } from "@/components/ui/button";
import type { ExtractBrandResponse } from "@/types/api-types";

interface BrandPreviewProps {
  data: ExtractBrandResponse;
  onConfirm: () => void;
  onEdit?: () => void;
  loading?: boolean;
}

/**
 * Convert RGB color to hex code
 * Supports formats: rgb(255, 255, 255), rgba(255, 255, 255, 1), or hex colors
 */
function rgbToHex(color: string): string {
  // If already hex, return as is
  if (color.startsWith('#')) {
    return color;
  }
  
  // Match rgb/rgba patterns
  const rgbMatch = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)/);
  if (rgbMatch) {
    const r = parseInt(rgbMatch[1]);
    const g = parseInt(rgbMatch[2]);
    const b = parseInt(rgbMatch[3]);
    return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
  }
  
  // Return original if format not recognized
  return color;
}

export function BrandPreview({ data, onConfirm, onEdit, loading }: BrandPreviewProps) {
  const hasContactInfo = data.contact_info && (data.contact_info.email || data.contact_info.phone || data.contact_info.address);
  const hasSocialLinks = data.social_links && data.social_links.length > 0;
  const hasColors = data.color_candidates && data.color_candidates.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-2xl mx-auto space-y-6"
    >
      {/* Header */}
      <div className="text-center space-y-2">
        <h3 className="text-2xl font-semibold text-foreground">
          Here's what we found
        </h3>
        <p className="text-sm text-muted-foreground">
          Review the extracted information and confirm to continue
        </p>
      </div>

      {/* Preview Card */}
      <div className="bg-card border border-border rounded-2xl p-6 space-y-6">
        {/* Logo */}
        {data.logo_url && (
          <div className="flex justify-center">
            <div className="w-24 h-24 rounded-xl overflow-hidden bg-muted flex items-center justify-center">
              <img 
                src={data.logo_url} 
                alt={`${data.brand_name} logo`}
                className="w-full h-full object-contain"
              />
            </div>
          </div>
        )}

        {/* Brand Name */}
        <div className="text-center">
          <h4 className="text-3xl font-bold text-foreground">
            {data.brand_name}
          </h4>
          {data.tagline && (
            <p className="mt-2 text-muted-foreground italic">
              "{data.tagline}"
            </p>
          )}
        </div>

        {/* Description */}
        {data.description && (
          <div className="pt-4 border-t border-border">
            <p className="text-sm text-foreground/80 leading-relaxed">
              {data.description}
            </p>
          </div>
        )}

        {/* Industry */}
        {data.industry && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Industry:</span>
            <span className="font-medium text-foreground">{data.industry}</span>
          </div>
        )}

        {/* Offer Cues */}
        {data.offer_cues && data.offer_cues.length > 0 && (
          <div className="space-y-2">
            <h5 className="text-sm font-medium text-muted-foreground">Value Propositions</h5>
            <div className="flex flex-wrap gap-2">
              {data.offer_cues.map((cue, idx) => (
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

        {/* Contact Info */}
        {hasContactInfo && (
          <div className="pt-4 border-t border-border space-y-3">
            <h5 className="text-sm font-medium text-muted-foreground">Contact Information</h5>
            <div className="grid gap-2">
              {data.contact_info?.email && (
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="w-4 h-4 text-muted-foreground" />
                  <a 
                    href={`mailto:${data.contact_info.email}`}
                    className="text-foreground hover:text-primary transition-colors"
                  >
                    {data.contact_info.email}
                  </a>
                </div>
              )}
              {data.contact_info?.phone && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-muted-foreground" />
                  <a 
                    href={`tel:${data.contact_info.phone}`}
                    className="text-foreground hover:text-primary transition-colors"
                  >
                    {data.contact_info.phone}
                  </a>
                </div>
              )}
              {data.contact_info?.address && (
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="w-4 h-4 text-muted-foreground" />
                  <span className="text-foreground">{data.contact_info.address}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Social Links */}
        {hasSocialLinks && (
          <div className="pt-4 border-t border-border space-y-3">
            <h5 className="text-sm font-medium text-muted-foreground">Social Media</h5>
            <div className="flex flex-wrap gap-2">
              {data.social_links?.map((link, idx) => {
                const domain = new URL(link).hostname.replace('www.', '');
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
              })}
            </div>
          </div>
        )}

        {/* Colors */}
        {hasColors && (
          <div className="pt-4 border-t border-border space-y-3 pb-2">
            <h5 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Palette className="w-4 h-4" />
              Brand Colors
            </h5>
            <div className="flex flex-wrap gap-3 mb-6">
              {data.color_candidates?.slice(0, 8).map((color, idx) => {
                const hexColor = rgbToHex(color);
                return (
                  <div
                    key={idx}
                    className="group relative flex flex-col items-center gap-1"
                  >
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

      {/* Actions */}
      <div className="flex gap-3 justify-center">
        {onEdit && (
          <Button
            variant="outline"
            onClick={onEdit}
            disabled={loading}
            className="min-w-[120px]"
          >
            Edit Details
          </Button>
        )}
        <Button
          onClick={onConfirm}
          disabled={loading}
          className="min-w-[120px]"
        >
          {loading ? "Processing..." : "Looks Good"}
        </Button>
      </div>
    </motion.div>
  );
}
