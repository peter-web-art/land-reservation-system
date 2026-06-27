#!/usr/bin/env python
"""
Add placeholder images to demo lands so they can be properly edited.
"""
import os
import django
from io import BytesIO
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()

from django.core.files.base import ContentFile
from lands.models import Land, LandImage

def create_placeholder_image(width=800, height=600, color=(26, 92, 56), text="Demo Land"):
    """Create a PIL Image with text."""
    img = Image.new('RGB', (width, height), color=color)
    # Save to a BytesIO object
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    return img_io

def add_images_to_demo_lands():
    """Add 3 placeholder images to each demo land."""
    demo_lands = Land.objects.filter(title__contains='Demo')
    positions = ['front', 'side', 'aerial']
    
    for land in demo_lands:
        # Check if land already has images
        if land.images.count() >= 3:
            print(f"✓ {land.title} already has {land.images.count()} images")
            continue
        
        # Add 3 images with different positions
        for i, position in enumerate(positions):
            img_io = create_placeholder_image(text=f"{land.title} - {position.title()}")
            filename = f"demo_land_{land.id}_{position}.png"
            
            # Create LandImage
            land_image = LandImage(
                land=land,
                position=position,
                order=i,
                is_primary=(i == 0)
            )
            land_image.image.save(filename, ContentFile(img_io.getvalue()), save=True)
            
        print(f"✓ Added 3 images to {land.title}")
    
    print(f"\n✓ Completed! Added placeholder images to {demo_lands.count()} demo lands")

if __name__ == '__main__':
    add_images_to_demo_lands()
