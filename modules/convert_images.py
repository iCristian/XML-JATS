from PIL import Image
import os
import glob

image_dir = "resources/manual_images"
# Get the numbered images the user added
images = glob.glob(os.path.join(image_dir, "0*.png"))
# Add the logo
images.append("resources/UV_color.png")

print(f"Found {len(images)} images to process: {images}")

for img_path in images:
    if not os.path.exists(img_path):
        print(f"Image not found: {img_path}")
        continue
        
    try:
        with Image.open(img_path) as img:
            # Convert to RGBA to preserve transparency
            img = img.convert('RGBA')
            # Save it back without interlacing
            img.save(img_path, "PNG", optimize=False, compress_level=0)
            print(f"Converted and saved: {img_path}")
    except Exception as e:
        print(f"Failed to convert {img_path}: {e}")
