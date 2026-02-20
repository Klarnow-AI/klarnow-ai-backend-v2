"""Image color extraction using K-means clustering."""

import os
from io import BytesIO
from typing import List

import colorsys
import numpy as np
import requests
from PIL import Image
from sklearn.cluster import KMeans

from app.modules.packs.extraction.schemas import ColorCandidate


def extract_brand_colors(
    image_url: str,
    max_colors: int = 5,
    resize: int = 256,
) -> List[ColorCandidate]:
    """
    Extract brand relevant colors from a logo or brand asset using K-means clustering.

    Args:
        image_url: URL or local path to the image
        max_colors: Maximum number of colors to extract
        resize: Resize dimension for faster processing

    Returns:
        List of ColorCandidate objects ordered by relevance
    """
    # Load and prepare image
    image = _load_image(image_url, resize)
    pixels = np.array(image).reshape(-1, 3)

    # Filter out noise (white, black, gray)
    pixels = _filter_noise_pixels(pixels)

    if len(pixels) == 0:
        return []

    # Cluster colors using K-means
    kmeans = KMeans(
        n_clusters=min(max_colors * 2, len(pixels)),
        n_init=10,
        random_state=42,
    )
    labels = kmeans.fit_predict(pixels)
    centers = kmeans.cluster_centers_.astype(int)

    counts = np.bincount(labels)

    # Build color data with metadata
    color_data = []
    for center, count in zip(centers, counts):
        hex_color = _rgb_to_hex(center)
        saturation = _rgb_saturation(center)

        color_data.append({
            "hex": hex_color,
            "count": count,
            "saturation": saturation,
        })

    # Sort by count and saturation
    color_data.sort(key=lambda c: (c["count"], c["saturation"]), reverse=True)

    # Deduplicate similar colors
    deduped = _deduplicate_colors(color_data)

    # Calculate confidence based on pixel count and saturation
    max_count = max(c["count"] for c in deduped) if deduped else 1

    color_candidates = []
    for rank, color_info in enumerate(deduped[:max_colors], start=1):
        # Confidence: combination of pixel frequency (normalized) and saturation
        count_ratio = color_info["count"] / max_count if max_count > 0 else 0
        saturation_score = color_info["saturation"]
        confidence = count_ratio * 0.7 + saturation_score * 0.3

        color_candidates.append(
            ColorCandidate(
                hex=color_info["hex"],
                confidence=round(confidence, 3),
                source="asset",
                rank=rank,
            )
        )

    return color_candidates


def _load_image(image_url: str, resize: int) -> Image.Image:
    """
    Load image from URL or local path.

    Args:
        image_url: URL or local file path
        resize: Target size for thumbnail

    Returns:
        PIL Image in RGB mode
    """
    # Check if it's a local file path or a URL
    if os.path.exists(image_url) or not image_url.startswith(("http://", "https://")):
        # Local file path
        image = Image.open(image_url).convert("RGBA")
    else:
        # URL
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGBA")

    # Handle transparency by compositing on white background
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert("RGB")

    # Resize for faster processing
    if resize:
        image.thumbnail((resize, resize))

    return image


def _filter_noise_pixels(pixels: np.ndarray) -> np.ndarray:
    """
    Filter out near-white, near-black, and near-gray pixels.

    Args:
        pixels: Array of RGB pixels (N, 3)

    Returns:
        Filtered array of pixels
    """
    filtered = []

    for r, g, b in pixels:
        if _is_near_white(r, g, b):
            continue
        if _is_near_black(r, g, b):
            continue
        filtered.append((r, g, b))

    return np.array(filtered) if filtered else np.array([]).reshape(0, 3)


def _deduplicate_colors(colors: List[dict], threshold: float = 0.1) -> List[dict]:
    """
    Remove similar colors based on distance threshold.

    Args:
        colors: List of color dicts with 'hex' key
        threshold: Distance threshold for similarity (0-1)

    Returns:
        Deduplicated list of colors
    """
    result = []

    for color in colors:
        if not any(
            _color_distance(color["hex"], existing["hex"]) < threshold
            for existing in result
        ):
            result.append(color)

    return result


def _rgb_to_hex(rgb) -> str:
    """Convert RGB tuple to hex string."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _rgb_saturation(rgb) -> float:
    """Calculate saturation (0-1) from RGB values."""
    r, g, b = [x / 255.0 for x in rgb]
    return colorsys.rgb_to_hsv(r, g, b)[1]


def _is_near_white(r: int, g: int, b: int, threshold: int = 240) -> bool:
    """Check if color is near white."""
    return r > threshold and g > threshold and b > threshold


def _is_near_black(r: int, g: int, b: int, threshold: int = 15) -> bool:
    """Check if color is near black."""
    return r < threshold and g < threshold and b < threshold


def _color_distance(hex1: str, hex2: str) -> float:
    """
    Calculate normalized Euclidean distance between two hex colors.

    Args:
        hex1: First hex color
        hex2: Second hex color

    Returns:
        Distance normalized to 0-1 range
    """
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
    return np.linalg.norm(np.array([r1, g1, b1]) - np.array([r2, g2, b2])) / 441.0


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
