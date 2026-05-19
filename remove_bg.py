from PIL import Image

# Input and output paths
input_path = r"c:\Users\Perfect Deal Tech\Downloads\pngtree-a-stylized-gas-station-icon-png-image_16471181.png"
output_path = r"c:\Users\Perfect Deal Tech\Desktop\Python\smartfuel\static\images\gas-station.png"

# Open the image
img = Image.open(input_path)

# Convert to RGBA if not already
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Get image data
data = img.getdata()

# Create new image data, making the background transparent
# The background appears to be a light blue color
new_data = []
for item in data:
    # If pixel is light blue-ish (close to background color), make it transparent
    # Background color is approximately RGB(207, 238, 255) or similar light blue
    if item[0] > 180 and item[1] > 200 and item[2] > 240:  # Light blue
        new_data.append((255, 255, 255, 0))  # Transparent
    else:
        new_data.append(item)

img.putdata(new_data)

# Save as PNG with transparency
img.save(output_path)
print(f"Background removed successfully! Saved to {output_path}")
