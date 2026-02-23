"""
Stremio APK Renamer & Recolorer - GUI
Provides a graphical interface for the Stremio APK renaming tool.
"""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Import the core renamer
from stremio_renamer import StremioRenamer, COLOR_THEMES, create_custom_theme


class RedirectText:
    """Redirect stdout/stderr to a tkinter Text widget (thread-safe via root.after)"""
    def __init__(self, text_widget, root, tag="stdout"):
        self.text_widget = text_widget
        self.root = root
        self.tag = tag

    def write(self, string):
        self.root.after(0, self._append, string)

    def _append(self, string):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, string, self.tag)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class ColorSwatch(tk.Canvas):
    """A small canvas that displays a gradient color preview"""
    def __init__(self, parent, colors, width=120, height=24, **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, **kwargs)
        self.draw_gradient(colors, width, height)

    def draw_gradient(self, colors, width, height):
        """Draw a simple horizontal gradient from the theme colors"""
        if not colors:
            return
        hex_colors = [c[0] for c in colors]
        # Convert #ffRRGGBB to #RRGGBB for tkinter
        tk_colors = []
        for c in hex_colors:
            c = c.lstrip('#')
            if len(c) == 8:
                c = c[2:]  # Strip alpha
            tk_colors.append(f"#{c}")

        n = len(tk_colors)
        if n == 1:
            self.create_rectangle(0, 0, width, height, fill=tk_colors[0], outline="")
            return

        segment_width = width / (n - 1)
        for i in range(n - 1):
            # Draw each segment as a solid block (simple but effective)
            x0 = int(i * segment_width)
            x1 = int((i + 1) * segment_width)
            # Blend between two colors across the segment
            c1 = self._hex_to_rgb(tk_colors[i])
            c2 = self._hex_to_rgb(tk_colors[i + 1])
            steps = max(x1 - x0, 1)
            for px in range(steps):
                t = px / steps
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
                color = f"#{r:02x}{g:02x}{b:02x}"
                self.create_line(x0 + px, 0, x0 + px, height, fill=color)

    @staticmethod
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


class StremioGUI:
    """Main GUI application"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Stremio APK Renamer & Recolorer")
        self.root.geometry("700x620")
        self.root.minsize(600, 550)
        self.root.resizable(True, True)

        # Theme colors for the GUI itself
        self.bg_color = "#1a1a2e"
        self.fg_color = "#e0e0e0"
        self.accent_color = "#7b5bf5"
        self.entry_bg = "#16213e"
        self.entry_fg = "#e0e0e0"
        self.btn_color = "#7b5bf5"
        self.btn_fg = "#ffffff"

        self.root.configure(bg=self.bg_color)

        # Configure ttk style
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        self.running = False

        self._build_ui()
        self._center_window()

    def _configure_styles(self):
        """Configure ttk widget styles"""
        self.style.configure("App.TFrame", background=self.bg_color)
        self.style.configure("App.TLabel", background=self.bg_color,
                             foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background=self.bg_color,
                             foreground=self.accent_color, font=("Segoe UI", 18, "bold"))
        self.style.configure("Sub.TLabel", background=self.bg_color,
                             foreground="#888888", font=("Segoe UI", 9))
        self.style.configure("App.TButton", font=("Segoe UI", 10))
        self.style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))
        self.style.configure("App.TCombobox", font=("Segoe UI", 10))
        self.style.configure("App.TLabelframe", background=self.bg_color,
                             foreground=self.fg_color, font=("Segoe UI", 10, "bold"))
        self.style.configure("App.TLabelframe.Label", background=self.bg_color,
                             foreground=self.accent_color, font=("Segoe UI", 10, "bold"))
        self.style.configure("App.TCheckbutton", background=self.bg_color,
                             foreground=self.fg_color, font=("Segoe UI", 10))

    def _build_ui(self):
        """Build the main UI"""
        main_frame = ttk.Frame(self.root, style="App.TFrame", padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(main_frame, text="Stremio APK Renamer",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(main_frame, text="Clone Stremio with a different name and color theme",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        # --- APK File ---
        file_frame = ttk.Frame(main_frame, style="App.TFrame")
        file_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(file_frame, text="APK File:", style="App.TLabel").pack(side=tk.LEFT)
        self.apk_var = tk.StringVar()
        self.apk_entry = tk.Entry(file_frame, textvariable=self.apk_var,
                                  bg=self.entry_bg, fg=self.entry_fg,
                                  insertbackground=self.fg_color,
                                  font=("Segoe UI", 10), relief="flat", bd=4)
        self.apk_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 4))
        ttk.Button(file_frame, text="Browse...", command=self._browse_apk,
                   style="App.TButton").pack(side=tk.RIGHT)

        # --- Output Directory ---
        out_frame = ttk.Frame(main_frame, style="App.TFrame")
        out_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(out_frame, text="Output Dir:", style="App.TLabel").pack(side=tk.LEFT)
        self.output_var = tk.StringVar()
        self.output_entry = tk.Entry(out_frame, textvariable=self.output_var,
                                     bg=self.entry_bg, fg=self.entry_fg,
                                     insertbackground=self.fg_color,
                                     font=("Segoe UI", 10), relief="flat", bd=4)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 4))
        ttk.Button(out_frame, text="Browse...", command=self._browse_output,
                   style="App.TButton").pack(side=tk.RIGHT)

        # --- Color Theme ---
        theme_frame = ttk.LabelFrame(main_frame, text="  Color Theme  ",
                                     style="App.TLabelframe", padding=10)
        theme_frame.pack(fill=tk.X, pady=(4, 8))

        self.theme_var = tk.StringVar(value="green")
        self.color_buttons = {}
        self.swatch_widgets = {}

        # Grid of color buttons
        colors_grid = ttk.Frame(theme_frame, style="App.TFrame")
        colors_grid.pack(fill=tk.X)

        themes = list(COLOR_THEMES.keys())
        cols = 4
        for i, theme_name in enumerate(themes):
            row, col = divmod(i, cols)
            btn_frame = ttk.Frame(colors_grid, style="App.TFrame")
            btn_frame.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            colors_grid.columnconfigure(col, weight=1)

            theme = COLOR_THEMES[theme_name]
            swatch = ColorSwatch(btn_frame, theme.gradient_colors, width=100, height=16,
                                 bg=self.bg_color)
            swatch.pack(anchor="w")

            rb = tk.Radiobutton(btn_frame, text=theme_name.capitalize(),
                                variable=self.theme_var, value=theme_name,
                                bg=self.bg_color, fg=self.fg_color,
                                selectcolor=self.entry_bg, activebackground=self.bg_color,
                                activeforeground=self.fg_color, font=("Segoe UI", 10),
                                command=self._on_theme_change)
            rb.pack(anchor="w")
            self.color_buttons[theme_name] = rb
            self.swatch_widgets[theme_name] = swatch

        # Custom color option
        custom_row = (len(themes) // cols) + 1
        custom_frame = ttk.Frame(colors_grid, style="App.TFrame")
        custom_frame.grid(row=custom_row, column=0, columnspan=cols, padx=4, pady=(8, 0), sticky="ew")

        rb_custom = tk.Radiobutton(custom_frame, text="Custom",
                                    variable=self.theme_var, value="custom",
                                    bg=self.bg_color, fg=self.fg_color,
                                    selectcolor=self.entry_bg, activebackground=self.bg_color,
                                    activeforeground=self.fg_color, font=("Segoe UI", 10),
                                    command=self._on_theme_change)
        rb_custom.pack(side=tk.LEFT)

        ttk.Label(custom_frame, text="  Hex:", style="App.TLabel").pack(side=tk.LEFT, padx=(12, 0))
        self.custom_color_var = tk.StringVar(value="#ff5500")
        self.custom_color_entry = tk.Entry(custom_frame, textvariable=self.custom_color_var,
                                           bg=self.entry_bg, fg=self.entry_fg,
                                           insertbackground=self.fg_color,
                                           font=("Segoe UI", 10), relief="flat", bd=4,
                                           width=10, state="disabled")
        self.custom_color_entry.pack(side=tk.LEFT, padx=4)

        ttk.Label(custom_frame, text="Hue shift:", style="App.TLabel").pack(side=tk.LEFT, padx=(8, 0))
        self.hue_shift_var = tk.StringVar(value="-100")
        self.hue_shift_entry = tk.Entry(custom_frame, textvariable=self.hue_shift_var,
                                        bg=self.entry_bg, fg=self.entry_fg,
                                        insertbackground=self.fg_color,
                                        font=("Segoe UI", 10), relief="flat", bd=4,
                                        width=6, state="disabled")
        self.hue_shift_entry.pack(side=tk.LEFT, padx=4)

        # --- Build Button ---
        btn_frame = ttk.Frame(main_frame, style="App.TFrame")
        btn_frame.pack(fill=tk.X, pady=(4, 8))

        self.build_btn = tk.Button(btn_frame, text="  ▶  Build APK  ",
                                   bg=self.btn_color, fg=self.btn_fg,
                                   activebackground="#6a4ae0", activeforeground="#ffffff",
                                   font=("Segoe UI", 12, "bold"), relief="flat", bd=0,
                                   cursor="hand2", command=self._start_build)
        self.build_btn.pack(side=tk.LEFT)

        self.status_label = ttk.Label(btn_frame, text="Ready", style="Sub.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=(16, 0))

        # --- Log Output ---
        log_frame = ttk.LabelFrame(main_frame, text="  Output Log  ",
                                   style="App.TLabelframe", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.log_text = tk.Text(log_frame, bg="#0f0f23", fg="#cccccc",
                                insertbackground="#cccccc", font=("Consolas", 9),
                                relief="flat", bd=4, wrap=tk.WORD, state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure text tags for coloring
        self.log_text.tag_configure("stdout", foreground="#cccccc")
        self.log_text.tag_configure("stderr", foreground="#ff6b6b")
        self.log_text.tag_configure("success", foreground="#85e16b")

    def _center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

    def _browse_apk(self):
        path = filedialog.askopenfilename(
            title="Select Stremio APK",
            filetypes=[("APK Files", "*.apk"), ("All files", "*.*")]
        )
        if path:
            self.apk_var.set(path)
            # Auto-set output dir if empty
            if not self.output_var.get():
                self.output_var.set(str(Path(path).parent / "output"))

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_var.set(path)

    def _on_theme_change(self):
        """Enable/disable custom color fields based on selection"""
        is_custom = self.theme_var.get() == "custom"
        state = "normal" if is_custom else "disabled"
        self.custom_color_entry.configure(state=state)
        self.hue_shift_entry.configure(state=state)

    def _log(self, msg, tag="stdout"):
        """Write a message to the log"""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, msg, tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def _start_build(self):
        """Validate inputs and start the build in a background thread"""
        if self.running:
            return

        apk_path = self.apk_var.get().strip()
        if not apk_path or not os.path.exists(apk_path):
            messagebox.showerror("Error", "Please select a valid APK file.")
            return

        color = self.theme_var.get()
        output_dir = self.output_var.get().strip() or None

        # Handle custom theme
        if color == "custom":
            custom_hex = self.custom_color_var.get().strip()
            if not custom_hex or not re.match(r'^#?[0-9a-fA-F]{6}$', custom_hex):
                messagebox.showerror("Error", "Please enter a valid hex color (e.g. #FF5500).")
                return
            try:
                hue_shift = int(self.hue_shift_var.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Hue shift must be an integer (-180 to 180).")
                return
            if not -180 <= hue_shift <= 180:
                messagebox.showerror("Error", "Hue shift must be between -180 and 180.")
                return
            COLOR_THEMES["custom"] = create_custom_theme("Custom", custom_hex, hue_shift)

        self.running = True
        self.build_btn.configure(state="disabled", text="  ⏳  Building...  ")
        self.status_label.configure(text="Building APK...")
        self._clear_log()

        # Run build in background thread
        thread = threading.Thread(target=self._run_build,
                                  args=(apk_path, color, output_dir), daemon=True)
        thread.start()

    def _run_build(self, apk_path, color, output_dir):
        """Run the build process (called in background thread)"""
        # Redirect stdout/stderr to the log widget
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = RedirectText(self.log_text, self.root, "stdout")
        sys.stderr = RedirectText(self.log_text, self.root, "stderr")

        try:
            renamer = StremioRenamer(
                apk_path=apk_path,
                color_theme=color,
                output_dir=output_dir
            )
            result = renamer.run()

            # Success
            self.root.after(0, self._build_complete, result, None)

        except Exception as e:
            self.root.after(0, self._build_complete, None, str(e))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _build_complete(self, result_path, error):
        """Called on the main thread when build finishes"""
        self.running = False
        self.build_btn.configure(state="normal", text="  ▶  Build APK  ")

        if error:
            self.status_label.configure(text="Build failed!")
            self._log(f"\n❌ FAILED: {error}\n", "stderr")
            messagebox.showerror("Build Failed", f"Error: {error}")
        else:
            self.status_label.configure(text="Build complete!")
            self._log(f"\n✅ APK saved to: {result_path}\n", "success")
            # Offer to open the output folder
            if messagebox.askyesno("Success!", f"APK built successfully!\n\n{result_path}\n\nOpen output folder?"):
                os.startfile(str(Path(result_path).parent))

    def run(self):
        """Start the GUI event loop"""
        self.root.mainloop()


def main():
    app = StremioGUI()
    app.run()


if __name__ == "__main__":
    main()
