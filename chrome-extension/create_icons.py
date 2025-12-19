"""
Skript zum Erstellen der Extension-Icons aus dem Logo
"""
from PIL import Image
import os

def create_icons():
    """Erstellt Icons in verschiedenen Größen aus dem Logo"""
    # Pfad zum Logo
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media', 'logo.png')
    
    if not os.path.exists(logo_path):
        print(f"Logo nicht gefunden: {logo_path}")
        print("Erstelle einfache Platzhalter-Icons...")
        create_placeholder_icons()
        return
    
    try:
        # Öffne das Logo
        img = Image.open(logo_path)
        
        # Erstelle Icons in verschiedenen Größen
        sizes = [16, 48, 128]
        icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
        os.makedirs(icons_dir, exist_ok=True)
        
        for size in sizes:
            # Resize mit hoher Qualität
            icon = img.resize((size, size), Image.Resampling.LANCZOS)
            icon_path = os.path.join(icons_dir, f'icon{size}.png')
            icon.save(icon_path, 'PNG')
            print(f"✓ Icon erstellt: {icon_path} ({size}x{size})")
        
        print("\nAlle Icons erfolgreich erstellt!")
        
    except Exception as e:
        print(f"Fehler beim Erstellen der Icons: {e}")
        print("Erstelle Platzhalter-Icons...")
        create_placeholder_icons()

def create_placeholder_icons():
    """Erstellt einfache Platzhalter-Icons"""
    from PIL import Image, ImageDraw, ImageFont
    
    sizes = [16, 48, 128]
    icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
    os.makedirs(icons_dir, exist_ok=True)
    
    for size in sizes:
        # Erstelle ein einfaches Icon mit Text
        img = Image.new('RGB', (size, size), color='#667eea')
        draw = ImageDraw.Draw(img)
        
        # Zeichne einen einfachen Musik-Noten-Symbol
        # Für kleine Icons: nur ein einfacher Kreis
        if size >= 48:
            # Größere Icons: Text oder Symbol
            try:
                # Versuche eine Schriftart zu verwenden
                font_size = size // 3
                draw.text((size//2, size//2), '🎵', anchor='mm')
            except:
                # Fallback: einfacher Kreis
                margin = size // 4
                draw.ellipse([margin, margin, size-margin, size-margin], 
                           fill='white', outline='white', width=2)
        else:
            # Kleine Icons: einfacher Kreis
            margin = size // 4
            draw.ellipse([margin, margin, size-margin, size-margin], 
                       fill='white', outline='white', width=1)
        
        icon_path = os.path.join(icons_dir, f'icon{size}.png')
        img.save(icon_path, 'PNG')
        print(f"✓ Platzhalter-Icon erstellt: {icon_path} ({size}x{size})")
    
    print("\nPlatzhalter-Icons erstellt!")
    print("Tipp: Ersetze diese später durch eigene Icons für ein besseres Aussehen.")

if __name__ == '__main__':
    create_icons()


