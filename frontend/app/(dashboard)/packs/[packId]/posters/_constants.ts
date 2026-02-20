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
    id: "a4_portrait",
    label: "A4 Portrait",
    width: 794,
    height: 1123,
    description: "Print, documents",
  },
  {
    id: "a5_landscape",
    label: "A5 Landscape",
    width: 559,
    height: 794,
    description: "Flyers, handouts",
  },
  {
    id: "instagram_square",
    label: "Instagram Square",
    width: 1080,
    height: 1080,
    description: "Feed post",
  },
  {
    id: "instagram_story",
    label: "Instagram Story",
    width: 1080,
    height: 1920,
    description: "Stories, Reels",
  },
];

export const DEFAULT_SIZE_PRESET = POSTER_SIZE_PRESETS[0];

export function getPresetById(id: string): SizePreset | undefined {
  return POSTER_SIZE_PRESETS.find((p) => p.id === id);
}
