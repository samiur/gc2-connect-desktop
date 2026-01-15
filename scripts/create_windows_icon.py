# ABOUTME: Script to create Windows .ico file from source PNG icon.
# ABOUTME: Generates multi-resolution icon for Windows applications.
"""Create Windows .ico file from source PNG."""

from pathlib import Path

from PIL import Image


def create_windows_icon(source_png: Path, output_ico: Path) -> None:
    """Create a Windows .ico file with multiple resolutions.

    Args:
        source_png: Path to the source PNG file (should be at least 256x256)
        output_ico: Path for the output .ico file
    """
    # Windows icon sizes (standard sizes for .ico files)
    sizes = [16, 24, 32, 48, 64, 128, 256]

    # Open source image
    img = Image.open(source_png)

    # Ensure RGBA mode for transparency support
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Create resized versions
    icons = []
    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)

    # Save as .ico with all sizes
    # The first image is used as the base, others are appended
    icons[0].save(
        output_ico,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:],
    )

    print(f"Created Windows icon: {output_ico}")
    print(f"  Sizes: {', '.join(f'{s}x{s}' for s in sizes)}")


def main() -> None:
    """Main entry point."""
    # Get paths relative to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    assets_dir = project_root / "assets"

    source_png = assets_dir / "icon.png"
    output_ico = assets_dir / "GC2Connect.ico"

    if not source_png.exists():
        # Try the 1024x1024 icon from the iconset
        source_png = assets_dir / "GC2Connect.iconset" / "icon_1024x1024.png"

    if not source_png.exists():
        print(f"Error: Source PNG not found at {source_png}")
        return

    create_windows_icon(source_png, output_ico)


if __name__ == "__main__":
    main()
