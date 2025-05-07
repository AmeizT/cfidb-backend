import random
import colorsys

def generate_oklch_color():
    """
    Generate a random OKLCH color with:
    - Lightness between 0.5 and 0.8 (to ensure visibility)
    - Chroma between 0.1 and 0.3 (for softer, less saturated colors)
    - Hue randomly distributed across the color wheel
    """
    hue = random.random()
    r, g, b = colorsys.hls_to_rgb(hue, 0.65, 0.5)
    
    # Simplified approximation
    L = 0.65
    C = 0.2
    H = round(hue * 360, 2)
    return f"oklch({L} {C} {H})"