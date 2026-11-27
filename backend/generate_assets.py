import os
from PIL import Image, ImageDraw

def generate_assets():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    public_dir = os.path.join(base_dir, "frontend", "public")
    samples_dir = os.path.join(public_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)

    # 1. Sample Paddy Crop
    img1 = Image.new('RGB', (600, 450), color=(34, 139, 34))
    d1 = ImageDraw.Draw(img1)
    d1.rectangle([(0, 0), (600, 150)], fill=(135, 206, 235))
    d1.rectangle([(0, 150), (600, 450)], fill=(46, 125, 50))
    for x in range(30, 580, 25):
        d1.line([(x, 450), (x - 10, 180)], fill=(76, 175, 80), width=6)
        d1.ellipse([(x - 25, 160), (x + 5, 200)], fill=(212, 175, 55))
    d1.rectangle([(20, 20), (580, 70)], fill=(0, 0, 0))
    d1.text((35, 30), 'Sample Demo: Paddy Crop (Fine) - Oryza Sativa', fill=(255, 255, 255))
    img1.save(os.path.join(samples_dir, 'sample_paddy.jpg'), quality=90)

    # 2. Sample Leaf Blight
    img2 = Image.new('RGB', (600, 450), color=(50, 150, 60))
    d2 = ImageDraw.Draw(img2)
    d2.polygon([(50, 225), (300, 50), (550, 225), (300, 400)], fill=(76, 175, 80))
    d2.line([(50, 225), (550, 225)], fill=(46, 125, 50), width=5)
    for cx, cy in [(220, 160), (380, 280), (320, 180)]:
        d2.ellipse([(cx-40, cy-40), (cx+40, cy+40)], fill=(101, 67, 33))
        d2.ellipse([(cx-25, cy-25), (cx+25, cy+25)], fill=(139, 69, 19))
        d2.ellipse([(cx-12, cy-12), (cx+12, cy+12)], fill=(60, 30, 10))
    d2.rectangle([(20, 20), (580, 70)], fill=(0, 0, 0))
    d2.text((35, 30), 'Sample Demo: Tomato Early Blight (Alternaria Solani)', fill=(255, 255, 255))
    img2.save(os.path.join(samples_dir, 'sample_leaf_blight.jpg'), quality=90)

    # 3. Sample Pesticide Bottle
    img3 = Image.new('RGB', (600, 450), color=(240, 244, 248))
    d3 = ImageDraw.Draw(img3)
    d3.rectangle([(220, 80), (380, 130)], fill=(30, 64, 175))
    d3.rectangle([(180, 130), (420, 400)], fill=(255, 255, 255), outline=(100, 116, 139), width=3)
    d3.rectangle([(200, 180), (400, 350)], fill=(238, 242, 255), outline=(99, 102, 241), width=2)
    d3.polygon([(300, 200), (340, 240), (300, 280), (260, 240)], fill=(239, 68, 68))
    d3.rectangle([(20, 20), (580, 70)], fill=(0, 0, 0))
    d3.text((35, 30), 'Sample Demo: Coragen 20SC Agrochemical Insecticide', fill=(255, 255, 255))
    img3.save(os.path.join(samples_dir, 'sample_pesticide.jpg'), quality=90)

    # 4. Sample Red Loam Soil
    img4 = Image.new('RGB', (600, 450), color=(184, 61, 39))
    d4 = ImageDraw.Draw(img4)
    import random
    random.seed(42)
    for _ in range(800):
        rx, ry = random.randint(0, 595), random.randint(0, 445)
        rr = random.randint(3, 12)
        c = random.choice([(140, 40, 25), (200, 80, 50), (120, 50, 30), (160, 70, 45)])
        d4.ellipse([(rx, ry), (rx+rr, ry+rr)], fill=c)
    d4.rectangle([(20, 20), (580, 70)], fill=(0, 0, 0))
    d4.text((35, 30), 'Sample Demo: Karnataka Red Laterite Loam Soil Profile', fill=(255, 255, 255))
    img4.save(os.path.join(samples_dir, 'sample_soil.jpg'), quality=90)

    # 5. PWA Icons
    def make_icon(size, filename):
        icon = Image.new('RGB', (size, size), color=(21, 128, 61))
        idraw = ImageDraw.Draw(icon)
        pad = size // 8
        idraw.ellipse([(pad, pad), (size - pad, size - pad)], fill=(34, 197, 94))
        cx, cy = size // 2, size // 2
        idraw.line([(cx, cy + size // 4), (cx, cy - size // 6)], fill=(255, 255, 255), width=max(2, size // 20))
        idraw.polygon([(cx, cy - size // 6), (cx + size // 4, cy - size // 4), (cx + size // 5, cy)], fill=(255, 255, 255))
        idraw.polygon([(cx, cy - size // 10), (cx - size // 4, cy - size // 5), (cx - size // 5, cy + size // 15)], fill=(255, 255, 255))
        icon.save(os.path.join(public_dir, filename))

    make_icon(192, 'pwa-192x192.png')
    make_icon(512, 'pwa-512x512.png')
    make_icon(64, 'favicon.ico')
    make_icon(180, 'apple-touch-icon.png')
    print('Generated all demo presets and PWA assets successfully.')

if __name__ == '__main__':
    generate_assets()
