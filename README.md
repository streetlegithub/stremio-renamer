# Stremio Renamer

A renamer and recolourer for 'Stremio', mainly used for having multiple accounts on the same device.
![GUI](assets/gui.png)

---

## What does it do

- Automatically changes the app name and icon colors
- Lets you pick a color theme (or create your own :o )
- Rebuilds and signs the APK
- Works with any Stremio APK (unless they break the formatting)

---

## OS Support

Tested on:
- Windows 10/11

Untested on:
- macOS
- Linux
- TempleOS

## Requirements

- **Python 3.13 or newer**
    - [Download Python](https://www.python.org/downloads/)
    - To check if you have Python installed, open a terminal (Command Prompt or PowerShell) and run:
      ```
      python --version
      ```
    - If you see a version number (e.g. `Python 3.13.x`), you have Python
    - If you see an error, install Python from the link above
    - Ensure Python is added to your Path by selecting `Add python.exe to PATH` on the installer
    - ![Add to PATH](assets/path.png)
- **Java JDK** (for signing the APK)
    - [Download Java JDK](https://adoptium.net/)
    - To check if you have Java JDK installed, open a terminal (Command Prompt or PowerShell) and run:
      ```
      java -version
      ```
    - If you see a version number (e.g. `openjdk version "11.x.xx" xxxx-xx-xx`), you have Java JDK
    - If you see an error, install Java JDK from the link above
- **Your own Stremio 1.9.5+ APK file** (download from [stremio.com](https://www.stremio.com/downloads))

---

## Installation

1. Click the green <> Code button → Download ZIP or clone this repository
   - *Extract the ZIP if required*
2. Open a terminal in the new folder e.g.:
    ```
    cd C:\Users\<your username>\Downloads\stremio-renamer-main\stremio-renamer-main
    ```
3. Install Python dependencies:
    ```
    pip install -r requirements.txt
    ```
4. Run the tool (see below)

---

## Usage

### Graphical User Interface (Recommended)

```sh
python stremio_renamer_gui.py
```

1. Select your Stremio APK file
2. Choose your color theme (or create a custom one)
3. Click "Build APK" and wait for the new APK

### Command Line

```sh
stremio_renamer.py [-h] [-o OUTPUT] [--custom-color CUSTOM_COLOR] [--hue-shift HUE_SHIFT] [--apktool APKTOOL] apk color
```

These arguments are required: `apk`, `color`

---

## What happens?

1. The tool automatically downloads and sets up **APKTool** (no manual steps needed).
2. Your APK is decompiled, themed, and rebuilt.
3. The new APK is signed with a debug key (easy for sideloading).

---

## Notes

- **You must provide your own APK file.** This tool does not distribute Stremio or any other APKs.
- The output APK is signed with a debug key.
- Only use APKs you have the legal right to modify.

---

## Troubleshooting

- Make sure both Python & Java JDK are installed and added to your PATH.
- If the APK won't install, enable "Install from unknown sources" on your device.
- If colors look wrong, try a different hue shift or base color.
- This tool is only intended for Stremio APKs

---

## Contributing

Pull requests and issues are welcome.

---

## License

See [LICENSE](LICENSE) for details. This project respects all third-party licenses (see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)).

---

## Disclaimer

This tool modifies APK files. Only use it with APKs you have the right to modify. The authors are not responsible for any misuse of this tool.
