"""
Stremio APK Renamer & Recolorer
Automates the process of cloning Stremio with different names and colored icons.

Requirements:
- Python 3.8+
- Pillow (pip install Pillow)
- apktool (automatically downloaded if not found)
- Java JDK (for jarsigner fallback)
- apksigner and zipalign (included in this directory)
"""

import os
import re
import sys
import shutil
import subprocess
import colorsys
import platform
import urllib.request
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from PIL import Image
import xml.etree.ElementTree as ET


@dataclass
class ColorTheme:
    """Represents a color theme with gradient stops for XML files and hue shift for PNGs"""
    name: str
    gradient_colors: List[Tuple[str, str]]  # List of (hex_color, offset) tuples
    hue_shift: int  # Hue shift value for PNG icons (-180 to 180)
    

# Predefined color themes
COLOR_THEMES: Dict[str, ColorTheme] = {
    "green": ColorTheme(
        name="Green",
        gradient_colors=[
            ("#ff2ca60c", "0.0"),
            ("#ff37b212", "0.07"),
            ("#ff55c540", "0.39"),
            ("#ff6ddb57", "0.54"),
            ("#ff85e16b", "0.76"),
        ],
        hue_shift=-140
    ),
    "blue": ColorTheme(
        name="Blue",
        gradient_colors=[
            ("#ff0c6da6", "0.0"),
            ("#ff1278b2", "0.07"),
            ("#ff4095c5", "0.39"),
            ("#ff57b0db", "0.54"),
            ("#ff6bc5e1", "0.76"),
        ],
        hue_shift=60
    ),
    "purple": ColorTheme(
        name="Purple",
        gradient_colors=[
            ("#ff6a0ca6", "0.0"),
            ("#ff7812b2", "0.07"),
            ("#ff9540c5", "0.39"),
            ("#ffb057db", "0.54"),
            ("#ffc56be1", "0.76"),
        ],
        hue_shift=120
    ),
    "red": ColorTheme(
        name="Red",
        gradient_colors=[
            ("#ffa60c0c", "0.0"),
            ("#ffb21212", "0.07"),
            ("#ffc54040", "0.39"),
            ("#ffdb5757", "0.54"),
            ("#ffe16b6b", "0.76"),
        ],
        hue_shift=-60
    ),
    "orange": ColorTheme(
        name="Orange",
        gradient_colors=[
            ("#ffa6520c", "0.0"),
            ("#ffb25e12", "0.07"),
            ("#ffc58040", "0.39"),
            ("#ffdb9a57", "0.54"),
            ("#ffe1b16b", "0.76"),
        ],
        hue_shift=-90
    ),
    "pink": ColorTheme(
        name="Pink",
        gradient_colors=[
            ("#fffecaf3", "0.0"),
            ("#fff98bdf", "0.25"),
            ("#fff65bd2", "0.5"),
            ("#ffef2ec6", "0.75"),
            ("#ffdd00b6", "1.0"),
        ],
        hue_shift=150
    ),
    "cyan": ColorTheme(
        name="Cyan",
        gradient_colors=[
            ("#ff0ca6a6", "0.0"),
            ("#ff12b2b2", "0.07"),
            ("#ff40c5c5", "0.39"),
            ("#ff57dbdb", "0.54"),
            ("#ff6be1e1", "0.76"),
        ],
        hue_shift=30
    ),
    "yellow": ColorTheme(
        name="Yellow",
        gradient_colors=[
            ("#ffa6a60c", "0.0"),
            ("#ffb2b212", "0.07"),
            ("#ffc5c540", "0.39"),
            ("#ffdbdb57", "0.54"),
            ("#ffe1e16b", "0.76"),
        ],
        hue_shift=-120
    ),
}


class StremioRenamer:
    """Main class for renaming and recoloring Stremio APK"""
    
    def __init__(self, apk_path: str, color_theme: str, output_dir: Optional[str] = None,
                 apktool_path: str = None):
        self.apk_path = Path(apk_path)
        self.color_theme = COLOR_THEMES.get(color_theme.lower())
        if not self.color_theme:
            raise ValueError(f"Unknown color theme: {color_theme}. Available: {list(COLOR_THEMES.keys())}")
        
        self.color_name = color_theme.capitalize()
        self.output_dir = Path(output_dir) if output_dir else self.apk_path.parent / "output"
        self.work_dir = self.output_dir / "work"
        self.script_dir = Path(__file__).parent
        
        # Setup apktool command (list)
        self.apktool_cmd = self._setup_apktool(apktool_path)
        # Human-readable apktool path for logging
        self.apktool_path = self.apktool_cmd[0] if isinstance(self.apktool_cmd, list) else str(self.apktool_cmd)
        
        # Files to modify
        self.drawable_xml_files = [
            "$ic_banner_foreground__0.xml",
            "$ic_stremio_logo__0.xml",
            "$ic_stremio_logo_expanded__0.xml",
            "$ic_stremio_splash_logo__0.xml",
        ]
        
        self.mipmap_folders = [
            "mipmap-mdpi",
            "mipmap-hdpi",
            "mipmap-xhdpi",
            "mipmap-xxhdpi",
            "mipmap-xxxhdpi",
        ]
        
        self.icon_files = ["ic_launcher.png", "ic_launcher_round.png"]
    
    def _setup_apktool(self, apktool_path: Optional[str]) -> list:
        """Setup apktool - returns command prefix list (e.g. ['apktool'] or ['java','-jar','apktool.jar'])"""
        # If user supplied a path, use it
        if apktool_path:
            if os.path.exists(apktool_path):
                if apktool_path.lower().endswith('.jar'):
                    return ["java", "-jar", str(apktool_path)]
                return [str(apktool_path)]
            else:
                print(f"Warning: Specified apktool path '{apktool_path}' not found, will try to download or find one")
        
        # Prefer wrapper script in script directory
        wrapper_name = "apktool.bat" if platform.system().lower() == "windows" else "apktool"
        wrapper_path = self.script_dir / wrapper_name
        if wrapper_path.exists():
            return [str(wrapper_path)]
        
        # If apktool available in PATH
        apktool_in_path = shutil.which("apktool")
        if apktool_in_path:
            return ["apktool"]
        
        # If jar exists in script dir, use java -jar
        jar_path = self.script_dir / "apktool.jar"
        if jar_path.exists():
            return ["java", "-jar", str(jar_path)]
        
        # Download apktool (creates jar + wrapper)
        print("Apktool not found, downloading...")
        try:
            wrapper_cmd = self._download_apktool()
            print(f"Apktool downloaded and wrapper created: {wrapper_cmd}")
            return wrapper_cmd
        except Exception as e:
            raise RuntimeError(f"Failed to download apktool: {e}")
    
    def _download_apktool(self) -> str:
        """Download apktool for the current platform"""
        system = platform.system().lower()
        
        # Use a known working version
        version = "2.9.3"
        
        # Download apktool.jar first (this is the main component)
        apktool_jar_path = self.script_dir / "apktool.jar"
        if not apktool_jar_path.exists():
            jar_url = f"https://github.com/iBotPeaches/Apktool/releases/download/v{version}/apktool_{version}.jar"
            print("Downloading apktool.jar...")
            
            try:
                with urllib.request.urlopen(jar_url) as response:
                    with open(apktool_jar_path, 'wb') as f:
                        f.write(response.read())
            except Exception as e:
                raise RuntimeError(f"Failed to download apktool.jar: {e}")
        
        # Create the appropriate wrapper script
        if system == "windows":
            script_path = self.script_dir / "apktool.bat"
            script_content = f'''@echo off
java -jar "%~dp0apktool.jar" %*
'''
        else:  # Unix-like systems
            script_path = self.script_dir / "apktool"
            script_content = f'''#!/bin/bash
java -jar "$(dirname "$0")/apktool.jar" "$@"
'''
        
        print(f"Creating apktool wrapper script...")
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable on Unix systems
        if system != "windows":
            script_path.chmod(0o755)
        
        # Return wrapper command as list
        return [str(script_path)]
    
    def run(self) -> str:
        """Execute the full renaming process"""
        print(f"\n{'='*60}")
        print(f"Stremio APK Renamer - Theme: {self.color_name}")
        print(f"{'='*60}\n")
        
        try:
            # Step 1: Setup directories
            self._setup_directories()
            
            # Step 2: Decompile APK
            self._decompile_apk()
            
            # Step 3: Modify AndroidManifest.xml
            self._modify_manifest()
            
            # Step 4: Modify strings.xml
            self._modify_strings()
            
            # Step 5: Modify drawable XML files (gradient colors)
            self._modify_drawable_xmls()
            
            # Step 6: Shift hue of PNG icons
            self._shift_icon_hues()
            
            # Step 7: Recompile APK
            output_apk = self._recompile_apk()
            
            # Step 8: Sign APK
            signed_apk = self._sign_apk(output_apk)
            
            # Step 9: Cleanup work directory
            self._cleanup()
            
            print(f"\n{'='*60}")
            print(f"SUCCESS! Output APK: {signed_apk}")
            print(f"{'='*60}\n")
            
            return str(signed_apk)
            
        except Exception as e:
            print(f"\nERROR: {e}")
            raise
    
    def _setup_directories(self):
        """Create necessary directories"""
        print("[1/9] Setting up directories...")
        
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  - Work directory: {self.work_dir}")
        print(f"  - Output directory: {self.output_dir}")
    
    def _decompile_apk(self):
        """Decompile the APK using apktool"""
        print("\n[2/9] Decompiling APK...")
        
        self.decompiled_dir = self.work_dir / "decompiled"
        
        cmd = self.apktool_cmd + [
            "d",
            str(self.apk_path),
            "-o", str(self.decompiled_dir),
            "-f"  # Force overwrite
        ]
        
        print(f"  - Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to decompile APK: {result.stderr}")
        
        print(f"  - Decompiled to: {self.decompiled_dir}")
    
    def _modify_manifest(self):
        """Modify AndroidManifest.xml to change package name"""
        print("\n[3/9] Modifying AndroidManifest.xml...")
        
        manifest_path = self.decompiled_dir / "AndroidManifest.xml"
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"AndroidManifest.xml not found at {manifest_path}")
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace package name
        old_package = "com.stremio.one"
        new_package = f"com.stremio.one.{self.color_name.lower()}"
        
        content = content.replace(old_package, new_package)
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  - Changed package: {old_package} -> {new_package}")
    
    def _modify_strings(self):
        """Modify strings.xml to change app name"""
        print("\n[4/9] Modifying strings.xml...")
        
        strings_path = self.decompiled_dir / "res" / "values" / "strings.xml"
        
        if not strings_path.exists():
            raise FileNotFoundError(f"strings.xml not found at {strings_path}")
        
        with open(strings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace app name
        old_name = '<string name="app_name">Stremio</string>'
        new_name = f'<string name="app_name">Stremio {self.color_name}</string>'
        
        content = content.replace(old_name, new_name)
        
        with open(strings_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  - Changed app name: Stremio -> Stremio {self.color_name}")
    
    def _modify_drawable_xmls(self):
        """Modify drawable XML files to change gradient colors"""
        print("\n[5/9] Modifying drawable XML files...")
        
        drawable_dir = self.decompiled_dir / "res" / "drawable-anydpi-v24"
        
        if not drawable_dir.exists():
            # Try alternative path
            drawable_dir = self.decompiled_dir / "res" / "drawable"
            if not drawable_dir.exists():
                print(f"  - Warning: drawable directory not found, skipping XML color changes")
                return
        
        for xml_file in self.drawable_xml_files:
            xml_path = drawable_dir / xml_file
            
            if not xml_path.exists():
                print(f"  - Warning: {xml_file} not found, skipping")
                continue
            
            self._update_gradient_colors(xml_path)
            print(f"  - Modified: {xml_file}")
    
    def _update_gradient_colors(self, xml_path: Path):
        """Update gradient colors in an XML file"""
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match gradient items
        # <item android:color="#ffXXXXXX" android:offset="X.XX" />
        pattern = r'<item\s+android:color="#[a-fA-F0-9]+"\s+android:offset="[\d.]+"'
        
        gradient_colors = self.color_theme.gradient_colors
        index = [0]  # Shared mutable counter across all replacements
        
        def replace_color(match):
            if index[0] < len(gradient_colors):
                color, offset = gradient_colors[index[0]]
                index[0] += 1
                return f'<item android:color="{color}" android:offset="{offset}"'
            return match.group(0)
        
        new_content = re.sub(pattern, replace_color, content)
        
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    def _shift_icon_hues(self):
        """Shift the hue of PNG icon files"""
        print("\n[6/9] Shifting icon hues...")
        
        hue_shift = self.color_theme.hue_shift
        
        for mipmap_folder in self.mipmap_folders:
            mipmap_path = self.decompiled_dir / "res" / mipmap_folder
            
            if not mipmap_path.exists():
                print(f"  - Warning: {mipmap_folder} not found, skipping")
                continue
            
            for icon_file in self.icon_files:
                icon_path = mipmap_path / icon_file
                
                if not icon_path.exists():
                    continue
                
                self._apply_hue_shift(icon_path, hue_shift)
                print(f"  - Processed: {mipmap_folder}/{icon_file}")
    
    def _apply_hue_shift(self, image_path: Path, hue_shift: int):
        """Apply hue shift to an image"""
        img = Image.open(image_path)
        
        # Convert to RGBA if necessary
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Get pixel data
        pixels = img.load()
        width, height = img.size
        
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                
                # Skip transparent pixels
                if a == 0:
                    continue
                
                # Convert RGB to HLS
                h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
                
                # Shift hue
                h = (h + hue_shift/360) % 1.0
                
                # Convert back to RGB
                r, g, b = colorsys.hls_to_rgb(h, l, s)
                
                pixels[x, y] = (int(r*255), int(g*255), int(b*255), a)
        
        img.save(image_path)
    
    def _recompile_apk(self) -> Path:
        """Recompile the APK using apktool"""
        print("\n[7/9] Recompiling APK...")
        
        output_apk = self.work_dir / f"Stremio_{self.color_name}_unsigned.apk"
        
        cmd = self.apktool_cmd + [
            "b",
            str(self.decompiled_dir),
            "-o", str(output_apk)
        ]
        
        print(f"  - Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to recompile APK: {result.stderr}")
        
        print(f"  - Created: {output_apk}")
        return output_apk
    
    def _check_apksigner_available(self) -> bool:
        """Check if apksigner is available"""
        apksigner_path = self.script_dir / "apksigner.bat"
        if not apksigner_path.exists():
            return False
        try:
            result = subprocess.run([str(apksigner_path), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _sign_apk(self, unsigned_apk: Path) -> Path:
        """Sign the APK with a debug keystore, preferring apksigner with zipalign before signing, 
        falling back to jarsigner with zipalign after signing"""
        print("\n[8/9] Signing APK...")

        signed_apk = self.output_dir / f"Stremio_{self.color_name}.apk"
        keystore_path = self.work_dir / "debug.keystore"
        aligned_apk = self.work_dir / f"Stremio_{self.color_name}_aligned.apk"

        # Generate a debug keystore if it doesn't exist
        if not keystore_path.exists():
            print("  - Generating debug keystore...")
            keytool_cmd = [
                "keytool", "-genkey",
                "-v",
                "-keystore", str(keystore_path),
                "-alias", "debug",
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "10000",
                "-storepass", "android",
                "-keypass", "android",
                "-dname", "CN=Debug, OU=Debug, O=Debug, L=Debug, ST=Debug, C=US"
            ]
            result = subprocess.run(keytool_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  - Warning: Could not generate keystore: {result.stderr}")
                print("  - Copying unsigned APK to output...")
                shutil.copy(unsigned_apk, signed_apk)
                return signed_apk

        # Try apksigner first (zipalign before signing)
        apksigner_available = self._check_apksigner_available()
        if apksigner_available:
            try:
                # Apply zipalign before signing
                print("  - Applying zipalign before signing...")
                zipalign_cmd = [
                    str(self.script_dir / "zipalign.exe"),
                    "-v", "4",
                    str(unsigned_apk),
                    str(aligned_apk)
                ]
                result = subprocess.run(zipalign_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"  - Warning: zipalign failed: {result.stderr}")
                    aligned_apk = unsigned_apk  # Use original if zipalign fails
                else:
                    print("  - APK aligned successfully")

                # Sign with apksigner
                print("  - Signing with apksigner...")
                signed_temp = self.work_dir / f"Stremio_{self.color_name}_signed.apk"
                apksigner_cmd = [
                    str(self.script_dir / "apksigner.bat"),
                    "sign",
                    "--ks", str(keystore_path),
                    "--ks-pass", "pass:android",
                    "--key-pass", "pass:android",
                    "--ks-key-alias", "debug",
                    "--out", str(signed_temp),
                    str(aligned_apk)
                ]
                result = subprocess.run(apksigner_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    shutil.copy(signed_temp, signed_apk)
                    print(f"  - Signed with apksigner: {signed_apk}")
                    return signed_apk
                else:
                    print(f"  - apksigner failed: {result.stderr}")
                    # Fall through to jarsigner
            except Exception as e:
                print(f"  - apksigner error: {e}")
                # Fall through to jarsigner

        # Fallback to jarsigner (zipalign after signing)
        print("  - Falling back to jarsigner...")
        try:
            jarsigner_cmd = [
                "jarsigner",
                "-verbose",
                "-sigalg", "SHA256withRSA",
                "-digestalg", "SHA-256",
                "-keystore", str(keystore_path),
                "-storepass", "android",
                "-keypass", "android",
                str(unsigned_apk),
                "debug"
            ]
            result = subprocess.run(jarsigner_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  - Warning: Could not sign APK: {result.stderr}")
                print("  - Copying unsigned APK to output...")
                shutil.copy(unsigned_apk, signed_apk)
                return signed_apk

            # Apply zipalign after signing
            print("  - Applying zipalign after signing...")
            zipalign_cmd = [
                str(self.script_dir / "zipalign.exe"),
                "-v", "4",
                str(unsigned_apk),  # jarsigner signs in place
                str(aligned_apk)
            ]
            result = subprocess.run(zipalign_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                shutil.copy(aligned_apk, signed_apk)
                print(f"  - Signed with jarsigner and aligned: {signed_apk}")
            else:
                print(f"  - Warning: zipalign failed: {result.stderr}")
                shutil.copy(unsigned_apk, signed_apk)
                print(f"  - Signed with jarsigner (no alignment): {signed_apk}")
        except FileNotFoundError:
            print("  - Warning: jarsigner not found, copying unsigned APK...")
            shutil.copy(unsigned_apk, signed_apk)
        
        return signed_apk

    def _cleanup(self):
        """Remove the work directory after successful build"""
        print("\n[9/9] Cleaning up...")
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
            print(f"  - Removed work directory: {self.work_dir}")


def create_custom_theme(name: str, base_color_hex: str, hue_shift: int) -> ColorTheme:
    """Create a custom color theme from a base color"""
    
    # Parse the base color
    base_color = base_color_hex.lstrip('#')
    if len(base_color) == 6:
        base_color = 'ff' + base_color  # Add alpha
    
    r = int(base_color[2:4], 16)
    g = int(base_color[4:6], 16)
    b = int(base_color[6:8], 16)
    
    # Convert to HLS
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    
    # Generate gradient colors with varying lightness
    gradient_colors = []
    lightness_offsets = [
        (0.0, -0.15),   # Darkest
        (0.07, -0.10),
        (0.39, 0.0),    # Base
        (0.54, 0.10),
        (0.76, 0.15),   # Lightest
    ]
    
    for offset, l_offset in lightness_offsets:
        new_l = max(0, min(1, l + l_offset))
        r2, g2, b2 = colorsys.hls_to_rgb(h, new_l, s)
        hex_color = f"#ff{int(r2*255):02x}{int(g2*255):02x}{int(b2*255):02x}"
        gradient_colors.append((hex_color, str(offset)))
    
    return ColorTheme(name=name, gradient_colors=gradient_colors, hue_shift=hue_shift)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Stremio APK Renamer & Recolorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available color themes:
  {', '.join(COLOR_THEMES.keys())}

Examples:
  python stremio_renamer.py stremio.apk green
  python stremio_renamer.py stremio.apk blue -o ./output
  python stremio_renamer.py stremio.apk custom --custom-color "#ff5500" --hue-shift -100
        """
    )
    
    parser.add_argument("apk", help="Path to the Stremio APK file")
    parser.add_argument("color", help="Color theme name or 'custom' for custom color")
    parser.add_argument("-o", "--output", help="Output directory (default: ./output)")
    parser.add_argument("--custom-color", help="Custom base color in hex format (e.g., #ff5500)")
    parser.add_argument("--hue-shift", type=int, help="Hue shift for PNG icons (-180 to 180)")
    parser.add_argument("--apktool", help="Path to apktool (auto-downloads if not specified)")
    
    args = parser.parse_args()
    
    # Validate APK exists
    if not os.path.exists(args.apk):
        print(f"Error: APK file not found: {args.apk}")
        sys.exit(1)
    
    # Handle custom color
    if args.color.lower() == "custom":
        if not args.custom_color:
            print("Error: --custom-color required when using 'custom' theme")
            sys.exit(1)
        if args.hue_shift is None:
            print("Error: --hue-shift required when using 'custom' theme")
            sys.exit(1)
        
        COLOR_THEMES["custom"] = create_custom_theme("Custom", args.custom_color, args.hue_shift)
    
    # Run the renamer
    try:
        renamer = StremioRenamer(
            apk_path=args.apk,
            color_theme=args.color,
            output_dir=args.output,
            apktool_path=args.apktool
        )
        renamer.run()
    except Exception as e:
        print(f"\nFailed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
