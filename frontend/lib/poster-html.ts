/**
 * Patches img tags in poster/ad HTML to improve loading on mobile and in PWAs.
 * Adds referrerpolicy="no-referrer" to avoid referrer-based blocking by CDNs.
 * Adds loading="eager" so thumbnails load immediately (avoids lazy-load quirks in PWA).
 */
export function patchPosterHtmlForImages(html: string): string {
  return html.replace(/<img\s+([^>]*?)>/gi, (match, attrs) => {
    const extra: string[] = [];
    if (!/referrerpolicy=/i.test(attrs)) extra.push('referrerpolicy="no-referrer"');
    if (!/loading=/i.test(attrs)) extra.push('loading="eager"');
    if (extra.length === 0) return match;
    return `<img ${attrs} ${extra.join(" ")}>`;
  });
}
