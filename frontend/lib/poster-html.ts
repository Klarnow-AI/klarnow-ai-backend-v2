/**
 * Patches img tags in poster/ad HTML to improve loading on mobile and in PWAs.
 * Adds referrerpolicy="no-referrer" to avoid referrer-based blocking by CDNs.
 */
export function patchPosterHtmlForImages(html: string): string {
  return html.replace(/<img\s+([^>]*?)>/gi, (match, attrs) => {
    if (/referrerpolicy=/i.test(attrs)) return match;
    return `<img ${attrs} referrerpolicy="no-referrer">`;
  });
}
