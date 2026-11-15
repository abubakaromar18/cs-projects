"""Tkinter desktop UI.

Layout (top to bottom):
  swatch + hex entry | RGB sliders | format rows with Copy buttons |
  contrast badges | harmony swatches | history strip | action buttons

"Pick from screen" takes a screenshot, shows it in a borderless full-screen
window with a magnifying loupe, and returns the pixel you click.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from .colors import RGB, contrast_ratio, harmonies, readable_text_color
from .history import History, default_history_path
from .model import PickerModel
from .sampler import CaptureUnavailable, PixelSource, default_grabber, magnify, sample

SWATCH = 22  # px size of small swatches


class ScreenPickerOverlay(tk.Toplevel):
    """Full-screen frozen screenshot with a loupe. Click = pick, Esc = cancel.

    Arrow keys nudge the cursor by one pixel for precise picking, and the
    mouse wheel changes the averaging radius (1x1, 3x3, 5x5 …).
    """

    LOUPE_HALF = 7   # loupe shows (2*7+1)^2 = 15x15 pixels
    LOUPE_ZOOM = 9   # each pixel drawn as 9x9

    def __init__(self, master: tk.Misc, shot: PixelSource, on_pick) -> None:
        super().__init__(master)
        from PIL import ImageTk  # Pillow is required for capture anyway

        self.shot, self.on_pick = shot, on_pick
        self.radius = 0
        self.pos = (shot.size[0] // 2, shot.size[1] // 2)
        self.overrideredirect(True)
        self.geometry(f"{shot.size[0]}x{shot.size[1]}+0+0")
        self.attributes("-topmost", True)
        self.canvas = tk.Canvas(self, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self._photo = ImageTk.PhotoImage(shot)  # keep a reference!
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")

        self.canvas.bind("<Motion>", lambda e: self._move(e.x, e.y))
        self.canvas.bind("<Button-1>", lambda e: self._pick())
        self.canvas.bind("<MouseWheel>", self._wheel)            # Windows/macOS
        self.canvas.bind("<Button-4>", lambda e: self._radius(+1))  # X11
        self.canvas.bind("<Button-5>", lambda e: self._radius(-1))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._pick())
        for key, (dx, dy) in {"Left": (-1, 0), "Right": (1, 0), "Up": (0, -1), "Down": (0, 1)}.items():
            self.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self._move(self.pos[0] + dx, self.pos[1] + dy))
        self.focus_force()
        self.grab_set()
        self._draw_loupe()

    def _wheel(self, e) -> None:
        self._radius(1 if e.delta > 0 else -1)

    def _radius(self, d: int) -> None:
        self.radius = max(0, min(4, self.radius + d))
        self._draw_loupe()

    def _move(self, x: int, y: int) -> None:
        w, h = self.shot.size
        self.pos = (max(0, min(w - 1, x)), max(0, min(h - 1, y)))
        self._draw_loupe()

    def _draw_loupe(self) -> None:
        c, z, half = self.canvas, self.LOUPE_ZOOM, self.LOUPE_HALF
        c.delete("loupe")
        x, y = self.pos
        size = (2 * half + 1) * z
        # Keep the loupe on-screen: flip to the other side near edges.
        ox = x + 24 if x + 24 + size < self.shot.size[0] else x - 24 - size
        oy = y + 24 if y + 24 + size + 28 < self.shot.size[1] else y - 24 - size - 28
        for j, row in enumerate(magnify(self.shot, x, y, half)):
            for i, px in enumerate(row):
                fill = px.hex if px else "#000000"
                c.create_rectangle(ox + i * z, oy + j * z, ox + (i + 1) * z, oy + (j + 1) * z,
                                   fill=fill, outline="", tags="loupe")
        # Outline the sampled block in the centre.
        r = self.radius
        c.create_rectangle(ox + (half - r) * z, oy + (half - r) * z,
                           ox + (half + r + 1) * z, oy + (half + r + 1) * z,
                           outline="white", width=2, tags="loupe")
        c.create_rectangle(ox, oy, ox + size, oy + size, outline="black", width=2, tags="loupe")
        col = sample(self.shot, x, y, self.radius)
        label = f"{col.hex.upper()}  ({x}, {y})  avg {2 * r + 1}x{2 * r + 1}"
        c.create_rectangle(ox, oy + size, ox + size, oy + size + 26, fill=col.hex, outline="black", tags="loupe")
        c.create_text(ox + size / 2, oy + size + 13, text=label,
                      fill=readable_text_color(col).hex, font=("TkDefaultFont", 9, "bold"), tags="loupe")

    def _pick(self) -> None:
        col = sample(self.shot, *self.pos, self.radius)
        self.destroy()
        self.on_pick(col)


class ColorPickerApp(ttk.Frame):
    def __init__(self, master: tk.Tk, model: PickerModel, grabber=None) -> None:
        super().__init__(master, padding=12)
        self.master: tk.Tk = master
        self.model = model
        self._grabber = grabber
        self._updating = False  # guards slider callbacks during programmatic updates
        self.grid(sticky="nsew")
        master.title("Screen Color Picker")
        master.resizable(False, False)
        self._build()
        self._bind_keys()
        model.subscribe(self._render)

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew")
        self.swatch = tk.Canvas(top, width=96, height=96, highlightthickness=1, highlightbackground="#888")
        self.swatch.grid(row=0, column=0, rowspan=3, padx=(0, 12))
        ttk.Label(top, text="Color (hex, rgb(), hsl(), name):").grid(row=0, column=1, sticky="w")
        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(top, textvariable=self.entry_var, width=24, font=("TkFixedFont", 12))
        self.entry.grid(row=1, column=1, sticky="ew")
        self.entry.bind("<Return>", self._on_entry)
        self.entry_status = ttk.Label(top, text="", foreground="#b00")
        self.entry_status.grid(row=2, column=1, sticky="w")

        sliders = ttk.LabelFrame(self, text="RGB", padding=6)
        sliders.grid(row=1, column=0, sticky="ew", pady=8)
        self.scales: dict[str, tk.Scale] = {}
        for i, ch in enumerate("rgb"):
            ttk.Label(sliders, text=ch.upper(), width=2).grid(row=i, column=0)
            s = tk.Scale(sliders, from_=0, to=255, orient="horizontal", length=300, showvalue=True,
                         command=lambda v, ch=ch: self._on_scale(ch, v))
            s.grid(row=i, column=1, sticky="ew")
            self.scales[ch] = s

        fmt = ttk.LabelFrame(self, text="Formats", padding=6)
        fmt.grid(row=2, column=0, sticky="ew")
        self.format_vars: dict[str, tk.StringVar] = {}
        for i, name in enumerate(["HEX", "RGB", "HSL", "HSV", "CMYK", "Name"]):
            ttk.Label(fmt, text=name, width=6).grid(row=i, column=0, sticky="w")
            var = tk.StringVar()
            ttk.Entry(fmt, textvariable=var, state="readonly", width=34).grid(row=i, column=1, padx=4)
            ttk.Button(fmt, text="Copy", width=6, command=lambda v=var: self.copy(v.get())).grid(row=i, column=2)
            self.format_vars[name] = var

        self.contrast_lbl = ttk.Label(self, text="", padding=(0, 6))
        self.contrast_lbl.grid(row=3, column=0, sticky="w")

        harm = ttk.LabelFrame(self, text="Harmonies (click to use)", padding=6)
        harm.grid(row=4, column=0, sticky="ew")
        self.harmony_canvas = tk.Canvas(harm, width=360, height=7 * (SWATCH + 4), highlightthickness=0)
        self.harmony_canvas.pack()

        hist = ttk.LabelFrame(self, text="History", padding=6)
        hist.grid(row=5, column=0, sticky="ew", pady=8)
        self.history_canvas = tk.Canvas(hist, width=360, height=SWATCH + 2, highlightthickness=0)
        self.history_canvas.pack()

        btns = ttk.Frame(self)
        btns.grid(row=6, column=0, sticky="ew")
        ttk.Button(btns, text="Pick from screen (Ctrl+P)", command=self.pick_from_screen).pack(side="left")
        ttk.Button(btns, text="System chooser…", command=self.system_chooser).pack(side="left", padx=6)
        ttk.Button(btns, text="Clear history", command=self.clear_history).pack(side="right")
        self.status = ttk.Label(self, text="", foreground="#555")
        self.status.grid(row=7, column=0, sticky="w", pady=(6, 0))

    def _bind_keys(self) -> None:
        self.master.bind("<Control-p>", lambda e: self.pick_from_screen())
        self.master.bind("<Control-c>", lambda e: self.copy(self.model.color.hex.upper())
                         if e.widget is not self.entry else None)

    # ------------------------------------------------------------ rendering
    def _render(self, c: RGB) -> None:
        self._updating = True
        try:
            self.swatch.delete("all")
            self.swatch.create_rectangle(0, 0, 98, 98, fill=c.hex, outline="")
            if self.focus_get() is not self.entry:
                self.entry_var.set(c.hex.upper())
            for ch, s in self.scales.items():
                s.set(getattr(c, ch))
            for name, text in c.formats().items():
                self.format_vars[name].set(text)
            on_w = contrast_ratio(c, RGB(255, 255, 255))
            on_b = contrast_ratio(c, RGB(0, 0, 0))
            grade = lambda r: "AAA" if r >= 7 else "AA" if r >= 4.5 else "AA large" if r >= 3 else "fail"
            self.contrast_lbl.config(text=f"Contrast vs white {on_w:.2f}:1 ({grade(on_w)})   "
                                          f"vs black {on_b:.2f}:1 ({grade(on_b)})")
            self._draw_harmonies(c)
            self._draw_history()
        finally:
            self._updating = False

    def _swatch_row(self, canvas: tk.Canvas, y: int, x0: int, colors: list[RGB]) -> None:
        for i, col in enumerate(colors):
            x = x0 + i * (SWATCH + 4)
            item = canvas.create_rectangle(x, y, x + SWATCH, y + SWATCH, fill=col.hex, outline="#777")
            canvas.tag_bind(item, "<Button-1>", lambda e, col=col: self.model.set_color(col, remember=True))

    def _draw_harmonies(self, c: RGB) -> None:
        cv = self.harmony_canvas
        cv.delete("all")
        for row, (name, cols) in enumerate(harmonies(c).items()):
            y = row * (SWATCH + 4)
            cv.create_text(0, y + SWATCH / 2, text=name, anchor="w")
            self._swatch_row(cv, y, 150, cols)

    def _draw_history(self) -> None:
        self.history_canvas.delete("all")
        self._swatch_row(self.history_canvas, 1, 0, list(self.model.history)[:14])

    # ------------------------------------------------------------ actions
    def _on_entry(self, _e=None) -> None:
        if self.model.set_text(self.entry_var.get()):
            self.entry_status.config(text="")
            self.master.focus_set()
        else:
            self.entry_status.config(text="Unrecognised color")

    def _on_scale(self, ch: str, value: str) -> None:
        if not self._updating:
            self.model.set_channel(ch, int(float(value)))

    def copy(self, text: str) -> None:
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        self.status.config(text=f"Copied {text}")

    def system_chooser(self) -> None:
        rgb, _hex = colorchooser.askcolor(color=self.model.color.hex, parent=self.master)
        if rgb:
            self.model.set_color(RGB(*(int(v) for v in rgb)), remember=True)

    def clear_history(self) -> None:
        self.model.history.clear()
        self._draw_history()

    def pick_from_screen(self) -> None:
        try:
            grab = self._grabber or default_grabber()
            self.master.withdraw()          # hide ourselves so we don't capture our own window
            self.master.update()
            self.master.after(150)          # give the window manager time to unmap
            shot = grab()
        except CaptureUnavailable as exc:
            self.master.deiconify()
            messagebox.showerror("Screen capture unavailable", str(exc), parent=self.master)
            return

        def done(col: RGB) -> None:
            self.model.set_color(col, remember=True)
            self.status.config(text=f"Picked {col.hex.upper()}")

        overlay = ScreenPickerOverlay(self.master, shot, done)
        overlay.bind("<Destroy>", lambda e: self.master.deiconify() if e.widget is overlay else None)


def run(initial: RGB | None = None) -> None:
    history = History(path=default_history_path())
    history.load()
    start = initial or (history[0] if len(history) else RGB(255, 136, 0))
    root = tk.Tk()
    model = PickerModel(start, history)
    ColorPickerApp(root, model)

    def on_close() -> None:
        history.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
