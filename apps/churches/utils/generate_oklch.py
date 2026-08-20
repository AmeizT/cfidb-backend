import random
import colorsys

def church_images_path(instance, filename):
    return 'churches/profile/{filename}'.format(filename=filename)


def generate_oklch_color():
    """
    Generate a random OKLCH color with:
    - Lightness between 0.5 and 0.8 (to ensure visibility)
    - Chroma between 0.1 and 0.3 (for softer, less saturated colors)
    - Hue randomly distributed across the color wheel
    """
    # Generate random hue
    hue = random.random()
    
    # Convert HSL to OKLCH
    # First, convert to RGB
    r, g, b = colorsys.hls_to_rgb(hue, 0.65, 0.5)
    
    # Convert RGB to OKLCH 
    # You might want to use a color conversion library like 'colormath' for precise conversion
    # This is a simplified approximation
    L = 0.65  # Lightness
    C = 0.2   # Chroma
    H = hue * 360  # Hue in degrees
    
    # Return as a string in oklch() format
    return f'oklch({L} {C} {H})'