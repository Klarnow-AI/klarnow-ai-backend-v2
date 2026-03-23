export type BrandContext = {
  brandName?: string;
  targetAudience?: string;
  mainAudience?: string[];
  coreOffer?: string;
  primaryCta?: string;
  primaryPain?: string;
  primaryOutcome?: string;
  heroAngle?: string;
  uspStatement?: string;
  uspProof?: string;
  logoUrl?: string;
  logoMarkup?: string;
  colorPalette?: { primary?: string; secondary?: string; accent?: string };
  fonts?: string[];
  brandPurpose?: string[];
  mission?: string;
  vision?: string;
  promise?: string;
  elevatorPitch?: string;
  proofPoints?: string[];
  audiencePersonas?: Array<{
    persona: string;
    needs: string[];
    painPoints: string[];
  }>;
  voiceArchetype?: string;
  voiceTraits?: string[];
  designCues?: string[];
  stylePalette?: string[];
  typographyDirection?: string;
  industry?: string;
};

export type BuilderAssistantMode = "launch" | "convert" | "polish" | "debug";
