import sys
from PIL import Image, ImageDraw, ImageFont

def create_pwa_icon(size, output_path):
    img = Image.new("RGBA", (size, size), (250, 248, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Background rounded square with emerald green
    padding = int(size * 0.08)
    radius = int(size * 0.22)
    emerald = (5, 150, 105, 255) # #059669
    
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=radius,
        fill=emerald
    )
    
    # Draw bus body (white)
    bus_w = int(size * 0.46)
    bus_h = int(size * 0.50)
    bus_x1 = (size - bus_w) // 2
    bus_y1 = int(size * 0.22)
    bus_x2 = bus_x1 + bus_w
    bus_y2 = bus_y1 + bus_h
    
    draw.rounded_rectangle(
        [bus_x1, bus_y1, bus_x2, bus_y2],
        radius=int(size * 0.08),
        fill=(255, 255, 255, 255)
    )
    
    # Bus windshield (emerald)
    ws_margin = int(size * 0.04)
    ws_h = int(size * 0.18)
    draw.rounded_rectangle(
        [bus_x1 + ws_margin, bus_y1 + ws_margin, bus_x2 - ws_margin, bus_y1 + ws_margin + ws_h],
        radius=int(size * 0.03),
        fill=emerald
    )
    
    # Headlights (orange #f97316)
    hl_radius = int(size * 0.03)
    hl_y = bus_y2 - int(size * 0.12)
    hl_x1 = bus_x1 + int(size * 0.07)
    hl_x2 = bus_x2 - int(size * 0.07)
    
    draw.ellipse([hl_x1 - hl_radius, hl_y - hl_radius, hl_x1 + hl_radius, hl_y + hl_radius], fill=(249, 115, 22, 255))
    draw.ellipse([hl_x2 - hl_radius, hl_y - hl_radius, hl_x2 + hl_radius, hl_y + hl_radius], fill=(249, 115, 22, 255))
    
    # Smile bumper line
    smile_y = bus_y2 - int(size * 0.07)
    draw.line([hl_x1 + int(size * 0.05), smile_y, hl_x2 - int(size * 0.05), smile_y], fill=emerald, width=int(size * 0.02))
    
    # Wheels (dark slate)
    wheel_w = int(size * 0.07)
    wheel_h = int(size * 0.06)
    wheel_y = bus_y2 - 2
    draw.rounded_rectangle([bus_x1 + int(size * 0.05), wheel_y, bus_x1 + int(size * 0.05) + wheel_w, wheel_y + wheel_h], radius=2, fill=(30, 41, 59, 255))
    draw.rounded_rectangle([bus_x2 - int(size * 0.05) - wheel_w, wheel_y, bus_x2 - int(size * 0.05), wheel_y + wheel_h], radius=2, fill=(30, 41, 59, 255))
    
    img.save(output_path, "PNG")
    print(f"Generated {output_path} ({size}x{size})")

create_pwa_icon(192, "assets/icons/icon-192.png")
create_pwa_icon(512, "assets/icons/icon-512.png")
