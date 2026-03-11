export type BrandContext = {
  brandName?: string;
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
  mission?: string;
  vision?: string;
  elevatorPitch?: string;
  proofPoints?: string[];
  audiencePersonas?: Array<{
    persona: string;
    needs: string[];
    painPoints: string[];
  }>;
  voiceArchetype?: string;
  designCues?: string[];
  industry?: string;
};
