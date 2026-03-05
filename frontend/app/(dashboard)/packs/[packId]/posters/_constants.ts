/** Poster/flyer size presets for the builder. */

export type SizePreset = {
  id: string;
  label: string;
  width: number;
  height: number;
  description?: string;
};

export const POSTER_SIZE_PRESETS: SizePreset[] = [
  {
    id: "4x5",
    label: "4x5 Feed",
    width: 1080,
    height: 1350,
    description: "Primary feed format",
  },
  {
    id: "9x16",
    label: "9x16 Story",
    width: 1080,
    height: 1920,
    description: "Stories and reels",
  },
  {
    id: "16x9",
    label: "16x9 Landscape",
    width: 1920,
    height: 1080,
    description: "Wide placements",
  },
  {
    id: "1x1",
    label: "1x1 Square",
    width: 1080,
    height: 1080,
    description: "Square placements",
  },
];

export const DEFAULT_SIZE_PRESET = POSTER_SIZE_PRESETS[0];

export function getPresetById(id: string): SizePreset | undefined {
  return POSTER_SIZE_PRESETS.find((p) => p.id === id);
}
