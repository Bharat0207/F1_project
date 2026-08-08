from pathlib import Path
import numpy as np
from PIL import Image

CACHE_DIR = Path("cache/driver_images")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def preprocess_driver(path):
    if not path:
        return None

    path = Path(path)
    if not path.exists():
        return None

    output = CACHE_DIR / f"{path.stem}_v2.png"

    if output.exists():
        return str(output)

    try:
        img = Image.open(path).convert("RGBA")
        data = np.array(img)

        # Vectorized black background removal
        r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
        black_pixels = (r < 30) & (g < 30) & (b < 30)
        data[black_pixels, 3] = 0

        img = Image.fromarray(data)

        # Trim transparent borders
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        # Crop to upper body (head & chest) so driver appears much larger
        w, h = img.size
        img = img.crop(
            (
                0,
                0,
                w,
                int(h * 0.50)  # Focus on top 50% for larger portrait feel
            )
        )

        # Higher resolution output
        img.thumbnail((400, 420))
        img.save(output)

        return str(output)
    except Exception:
        return str(path)