# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageFilter


try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9
    RESAMPLE = Image.LANCZOS


SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
MIN_SIZE = 1


@dataclass
class LoadedImage:
    path: Path
    image: Image.Image

    @property
    def label(self) -> str:
        return f"{self.path.name}  {self.image.width}x{self.image.height}"


@dataclass
class CompositeOptions:
    auto_resize: bool = True
    fit_mode: str = "stretch"  # stretch, contain, cover
    size_source: str = "selection"  # selection, patch, custom
    custom_size: Tuple[int, int] = (512, 512)
    scale_percent: float = 100.0
    snap_to_patch_aspect: bool = False
    black_to_alpha: bool = True
    black_threshold: int = 18
    black_softness: int = 18
    feather: int = 1
    opacity: float = 1.0


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def normalize_box(region: Sequence[int]) -> Tuple[int, int, int, int]:
    if len(region) != 4:
        raise ValueError("region must be x,y,w,h")
    x, y, w, h = (int(round(float(v))) for v in region)
    if w < 0:
        x += w
        w = -w
    if h < 0:
        y += h
        h = -h
    return x, y, max(MIN_SIZE, w), max(MIN_SIZE, h)


def choose_destination_size(
    region_size: Tuple[int, int],
    patch_size: Tuple[int, int],
    options: CompositeOptions,
) -> Tuple[int, int]:
    scale = max(0.01, float(options.scale_percent) / 100.0)
    if options.size_source == "patch":
        width, height = patch_size
    elif options.size_source == "custom":
        width, height = options.custom_size
    else:
        width, height = region_size
    width = max(MIN_SIZE, int(round(width * scale)))
    height = max(MIN_SIZE, int(round(height * scale)))

    if options.snap_to_patch_aspect and patch_size[0] > 0 and patch_size[1] > 0:
        aspect = patch_size[0] / patch_size[1]
        if width / height > aspect:
            width = max(MIN_SIZE, int(round(height * aspect)))
        else:
            height = max(MIN_SIZE, int(round(width / aspect)))
    return width, height


def resize_patch_to_target(
    patch: Image.Image,
    target_size: Tuple[int, int],
    options: CompositeOptions,
) -> Image.Image:
    target_w, target_h = target_size
    patch = patch.convert("RGBA")
    if not options.auto_resize:
        layer = Image.new("RGBA", target_size, (0, 0, 0, 0))
        layer.paste(patch.crop((0, 0, min(patch.width, target_w), min(patch.height, target_h))), (0, 0))
        return layer

    if patch.size == target_size:
        return patch

    fit_mode = options.fit_mode
    if fit_mode == "contain":
        ratio = min(target_w / patch.width, target_h / patch.height)
        new_size = (max(1, int(round(patch.width * ratio))), max(1, int(round(patch.height * ratio))))
        resized = patch.resize(new_size, RESAMPLE)
        layer = Image.new("RGBA", target_size, (0, 0, 0, 0))
        layer.paste(resized, ((target_w - new_size[0]) // 2, (target_h - new_size[1]) // 2))
        return layer

    if fit_mode == "cover":
        ratio = max(target_w / patch.width, target_h / patch.height)
        new_size = (max(1, int(round(patch.width * ratio))), max(1, int(round(patch.height * ratio))))
        resized = patch.resize(new_size, RESAMPLE)
        left = max(0, (new_size[0] - target_w) // 2)
        top = max(0, (new_size[1] - target_h) // 2)
        return resized.crop((left, top, left + target_w, top + target_h))

    return patch.resize(target_size, RESAMPLE)


def build_black_mask(image: Image.Image, threshold: int, softness: int) -> Image.Image:
    rgb = image.convert("RGB")
    r, g, b = rgb.split()
    bright = ImageChops.lighter(ImageChops.lighter(r, g), b)
    threshold = clamp(int(threshold), 0, 255)
    softness = max(1, int(softness))
    upper = min(255, threshold + softness)

    def ramp(v: int) -> int:
        if v <= threshold:
            return 0
        if v >= upper:
            return 255
        return int(round((v - threshold) * 255 / (upper - threshold)))

    return bright.point(ramp, mode="L")


def build_mask(image: Image.Image, options: CompositeOptions) -> Image.Image:
    image = image.convert("RGBA")
    mask = image.getchannel("A")
    if options.black_to_alpha:
        black_mask = build_black_mask(image, options.black_threshold, options.black_softness)
        mask = ImageChops.multiply(mask, black_mask)
    if options.feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(float(options.feather)))
    opacity = clamp(int(round(float(options.opacity) * 255)), 0, 255)
    if opacity < 255:
        mask = mask.point(lambda v: int(v * opacity / 255), mode="L")
    return mask


def composite_images(
    base: Image.Image,
    patch: Image.Image,
    region: Sequence[int],
    options: Optional[CompositeOptions] = None,
) -> Image.Image:
    options = options or CompositeOptions()
    base = base.convert("RGBA")
    patch = patch.convert("RGBA")
    x, y, region_w, region_h = normalize_box(region)
    dest_w, dest_h = choose_destination_size((region_w, region_h), patch.size, options)
    if options.snap_to_patch_aspect:
        x += (region_w - dest_w) // 2
        y += (region_h - dest_h) // 2

    prepared = resize_patch_to_target(patch, (dest_w, dest_h), options)
    mask = build_mask(prepared, options)

    output = base.copy()
    base_x = max(0, x)
    base_y = max(0, y)
    patch_x = max(0, -x)
    patch_y = max(0, -y)
    paste_w = min(dest_w - patch_x, base.width - base_x)
    paste_h = min(dest_h - patch_y, base.height - base_y)
    if paste_w <= 0 or paste_h <= 0:
        return output

    box = (patch_x, patch_y, patch_x + paste_w, patch_y + paste_h)
    output.paste(prepared.crop(box), (base_x, base_y), mask.crop(box))
    return output


def configure_tcl_tk_paths() -> None:
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    if getattr(sys, "frozen", False):
        base_text = str(base)
        if base_text not in sys.path:
            sys.path.insert(0, base_text)
    candidates = [
        base / "tcl",
        Path(sys.prefix) / "tcl",
        Path(sys.base_prefix) / "tcl",
    ]
    for tcl_root in candidates:
        tcl_dir = tcl_root / "tcl8.6"
        tk_dir = tcl_root / "tk8.6"
        if tcl_dir.exists() and tk_dir.exists():
            os.environ.setdefault("TCL_LIBRARY", str(tcl_dir))
            os.environ.setdefault("TK_LIBRARY", str(tk_dir))
            return


class RegionCompositorApp:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.base: Optional[LoadedImage] = None
        self.patch: Optional[LoadedImage] = None
        self.preview_photo = None
        self.display_image_size = (1, 1)
        self.display_offset = (0, 0)
        self.display_scale = 1.0
        self.drag_mode = None
        self.drag_start = (0, 0)
        self.drag_original = (0, 0, 1, 1)
        self._updating = False

        self.x_var = tk.IntVar(value=0)
        self.y_var = tk.IntVar(value=0)
        self.w_var = tk.IntVar(value=512)
        self.h_var = tk.IntVar(value=512)
        self.size_source_var = tk.StringVar(value="selection")
        self.custom_w_var = tk.IntVar(value=512)
        self.custom_h_var = tk.IntVar(value=512)
        self.scale_var = tk.DoubleVar(value=100.0)
        self.auto_resize_var = tk.BooleanVar(value=True)
        self.fit_mode_var = tk.StringVar(value="stretch")
        self.snap_aspect_var = tk.BooleanVar(value=False)
        self.black_alpha_var = tk.BooleanVar(value=True)
        self.black_threshold_var = tk.IntVar(value=18)
        self.black_softness_var = tk.IntVar(value=18)
        self.feather_var = tk.IntVar(value=1)
        self.opacity_var = tk.DoubleVar(value=100.0)
        self.status_var = tk.StringVar(value="Load a base image and a patch image.")
        self.base_label_var = tk.StringVar(value="Base: not loaded")
        self.patch_label_var = tk.StringVar(value="Patch: not loaded")

        self.root.title("Region Compositor")
        self.root.geometry("1180x760")
        self._configure_style()
        self._build_ui()
        self._bind_events()

    def _configure_style(self):
        style = self.ttk.Style()
        try:
            style.theme_use("clam")
        except self.tk.TclError:
            pass
        style.configure("TButton", padding=(8, 5))
        style.configure("Tool.TButton", padding=(6, 4))
        style.configure("Status.TLabel", foreground="#444")

    def _build_ui(self):
        tk = self.tk
        ttk = self.ttk
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        right = ttk.Frame(main, width=350)
        main.add(left, weight=4)
        main.add(right, weight=0)

        self.canvas = tk.Canvas(left, background="#202020", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        ttk.Label(left, textvariable=self.status_var, style="Status.TLabel").pack(fill=tk.X, padx=8, pady=(0, 8))

        controls = ttk.Frame(right)
        controls.pack(fill=tk.BOTH, expand=False, padx=8, pady=8)
        self._build_file_section(controls)
        self._build_region_section(controls)
        self._build_size_section(controls)
        self._build_fit_section(controls)
        self._build_mask_section(controls)
        self._build_save_section(controls)

    def _build_file_section(self, parent):
        ttk = self.ttk
        frame = ttk.LabelFrame(parent, text="Images")
        frame.pack(fill="x", pady=(0, 8))
        ttk.Button(frame, text="Load base", command=self.open_base).pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(frame, textvariable=self.base_label_var).pack(fill="x", padx=8)
        ttk.Button(frame, text="Load patch", command=self.open_patch).pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(frame, textvariable=self.patch_label_var).pack(fill="x", padx=8, pady=(0, 8))

    def _build_region_section(self, parent):
        ttk = self.ttk
        frame = ttk.LabelFrame(parent, text="Region on base")
        frame.pack(fill="x", pady=(0, 8))
        grid = ttk.Frame(frame)
        grid.pack(fill="x", padx=8, pady=8)
        for row, (label, var) in enumerate(
            (("X", self.x_var), ("Y", self.y_var), ("W", self.w_var), ("H", self.h_var))
        ):
            ttk.Label(grid, text=label, width=3).grid(row=row // 2, column=(row % 2) * 2, sticky="w", padx=(0, 4), pady=2)
            box = ttk.Spinbox(grid, from_=-20000, to=20000, textvariable=var, width=9, command=self.render)
            box.grid(row=row // 2, column=(row % 2) * 2 + 1, sticky="ew", padx=(0, 10), pady=2)
            box.bind("<Return>", lambda _e: self.render())
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)

        row = ttk.Frame(frame)
        row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(row, text="Full base", command=self.use_full_base).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(row, text="Patch size", command=self.use_patch_size).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row, text="Match aspect", command=self.match_patch_aspect).pack(side="left", fill="x", expand=True, padx=(4, 0))

    def _build_size_section(self, parent):
        ttk = self.ttk
        frame = ttk.LabelFrame(parent, text="Composite size")
        frame.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(
            frame,
            text="Layer-size toggle: use selected layer size",
            variable=self.snap_aspect_var,
            command=self.render,
        ).pack(anchor="w", padx=8, pady=(8, 2))
        source = ttk.Combobox(
            frame,
            state="readonly",
            values=("selection", "patch", "custom"),
            textvariable=self.size_source_var,
        )
        source.pack(fill="x", padx=8, pady=4)
        source.bind("<<ComboboxSelected>>", lambda _e: self.render())

        custom = ttk.Frame(frame)
        custom.pack(fill="x", padx=8, pady=4)
        ttk.Label(custom, text="Custom W").pack(side="left")
        ttk.Spinbox(custom, from_=1, to=20000, textvariable=self.custom_w_var, width=7, command=self.render).pack(
            side="left", padx=(4, 10)
        )
        ttk.Label(custom, text="H").pack(side="left")
        ttk.Spinbox(custom, from_=1, to=20000, textvariable=self.custom_h_var, width=7, command=self.render).pack(
            side="left", padx=(4, 0)
        )
        ttk.Label(frame, text="Scale %").pack(anchor="w", padx=8, pady=(4, 0))
        ttk.Scale(frame, from_=5, to=400, variable=self.scale_var, command=lambda _v: self.render()).pack(
            fill="x", padx=8, pady=(0, 8)
        )

    def _build_fit_section(self, parent):
        ttk = self.ttk
        frame = ttk.LabelFrame(parent, text="Resolution / ratio")
        frame.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(frame, text="Auto-resize patch to composite size", variable=self.auto_resize_var, command=self.render).pack(
            anchor="w", padx=8, pady=(8, 4)
        )
        combo = ttk.Combobox(
            frame,
            state="readonly",
            values=("stretch", "contain", "cover"),
            textvariable=self.fit_mode_var,
        )
        combo.pack(fill="x", padx=8, pady=(0, 8))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.render())

    def _build_mask_section(self, parent):
        ttk = self.ttk
        frame = ttk.LabelFrame(parent, text="Mask / blend")
        frame.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(frame, text="Treat black background as transparent", variable=self.black_alpha_var, command=self.render).pack(
            anchor="w", padx=8, pady=(8, 4)
        )
        self._slider(frame, "Black threshold", self.black_threshold_var, 0, 80)
        self._slider(frame, "Black softness", self.black_softness_var, 1, 80)
        self._slider(frame, "Feather", self.feather_var, 0, 20)
        self._slider(frame, "Opacity", self.opacity_var, 0, 100)

    def _slider(self, parent, label, var, start, end):
        ttk = self.ttk
        ttk.Label(parent, text=label).pack(anchor="w", padx=8)
        ttk.Scale(parent, from_=start, to=end, variable=var, command=lambda _v: self.render()).pack(
            fill="x", padx=8, pady=(0, 6)
        )

    def _build_save_section(self, parent):
        ttk = self.ttk
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(0, 8))
        ttk.Button(frame, text="Refresh preview", command=self.render).pack(fill="x", pady=(0, 4))
        ttk.Button(frame, text="Save PNG...", command=self.save_png).pack(fill="x")

    def _bind_events(self):
        self.canvas.bind("<Configure>", lambda _e: self.render())
        self.canvas.bind("<ButtonPress-1>", self.on_pointer_down)
        self.canvas.bind("<B1-Motion>", self.on_pointer_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_pointer_up)
        for var in (
            self.x_var,
            self.y_var,
            self.w_var,
            self.h_var,
            self.custom_w_var,
            self.custom_h_var,
        ):
            var.trace_add("write", lambda *_: self.render())

    def options(self) -> CompositeOptions:
        return CompositeOptions(
            auto_resize=bool(self.auto_resize_var.get()),
            fit_mode=self.fit_mode_var.get(),
            size_source=self.size_source_var.get(),
            custom_size=(max(1, self.custom_w_var.get()), max(1, self.custom_h_var.get())),
            scale_percent=float(self.scale_var.get()),
            snap_to_patch_aspect=bool(self.snap_aspect_var.get()),
            black_to_alpha=bool(self.black_alpha_var.get()),
            black_threshold=int(float(self.black_threshold_var.get())),
            black_softness=int(float(self.black_softness_var.get())),
            feather=int(float(self.feather_var.get())),
            opacity=float(self.opacity_var.get()) / 100.0,
        )

    def current_region(self) -> Tuple[int, int, int, int]:
        return normalize_box((self.x_var.get(), self.y_var.get(), self.w_var.get(), self.h_var.get()))

    def set_region(self, x: int, y: int, w: int, h: int):
        x, y, w, h = normalize_box((x, y, w, h))
        self._updating = True
        self.x_var.set(int(x))
        self.y_var.set(int(y))
        self.w_var.set(int(w))
        self.h_var.set(int(h))
        self._updating = False
        self.render()

    def open_base(self):
        path = self.ask_image_path()
        if path:
            self.load_base(path)

    def open_patch(self):
        path = self.ask_image_path()
        if path:
            self.load_patch(path)

    def ask_image_path(self) -> Optional[Path]:
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            filetypes=(("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("All files", "*.*"))
        )
        return Path(path) if path else None

    def load_base(self, path: Path):
        image = Image.open(path).convert("RGBA")
        self.base = LoadedImage(path, image)
        self.base_label_var.set(f"Base: {self.base.label}")
        if self.w_var.get() == 512 and self.h_var.get() == 512:
            self.set_region(0, 0, image.width, image.height)
        else:
            self.render()

    def load_patch(self, path: Path):
        image = Image.open(path).convert("RGBA")
        self.patch = LoadedImage(path, image)
        self.patch_label_var.set(f"Patch: {self.patch.label}")
        if self.base and self.size_source_var.get() == "patch":
            self.use_patch_size()
        self.render()

    def use_full_base(self):
        if not self.base:
            return
        self.set_region(0, 0, self.base.image.width, self.base.image.height)

    def use_patch_size(self):
        if not self.patch:
            return
        x, y, _w, _h = self.current_region()
        self.size_source_var.set("patch")
        self.set_region(x, y, self.patch.image.width, self.patch.image.height)

    def match_patch_aspect(self):
        if not self.patch:
            return
        x, y, w, h = self.current_region()
        cx = x + w // 2
        cy = y + h // 2
        aspect = self.patch.image.width / self.patch.image.height
        if w / h > aspect:
            w = max(1, int(round(h * aspect)))
        else:
            h = max(1, int(round(w / aspect)))
        self.set_region(cx - w // 2, cy - h // 2, w, h)

    def compose_for_preview(self) -> Optional[Image.Image]:
        if self.base and self.patch:
            return composite_images(self.base.image, self.patch.image, self.current_region(), self.options())
        if self.base:
            return self.base.image
        if self.patch:
            return self.patch.image
        return None

    def render(self):
        if getattr(self, "_updating", False):
            return
        image = self.compose_for_preview()
        self.canvas.delete("all")
        if image is None:
            self.status_var.set("Load a base image and a patch image.")
            return

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        scale = min(canvas_w / image.width, canvas_h / image.height, 1.0)
        display_w = max(1, int(round(image.width * scale)))
        display_h = max(1, int(round(image.height * scale)))
        display = image.resize((display_w, display_h), RESAMPLE) if image.size != (display_w, display_h) else image

        from PIL import ImageTk

        self.preview_photo = ImageTk.PhotoImage(display)
        offset_x = (canvas_w - display_w) // 2
        offset_y = (canvas_h - display_h) // 2
        self.display_image_size = (display_w, display_h)
        self.display_offset = (offset_x, offset_y)
        self.display_scale = scale
        self.canvas.create_image(offset_x, offset_y, anchor="nw", image=self.preview_photo)

        if self.base:
            self.draw_region_overlay()
        if self.base and self.patch:
            x, y, w, h = self.current_region()
            opts = self.options()
            dest = choose_destination_size((w, h), self.patch.image.size, opts)
            self.status_var.set(
                f"Base {self.base.image.width}x{self.base.image.height} | "
                f"Patch {self.patch.image.width}x{self.patch.image.height} | "
                f"Composite {dest[0]}x{dest[1]} | {opts.fit_mode}"
            )

    def draw_region_overlay(self):
        x, y, w, h = self.current_region()
        if self.patch:
            dest_w, dest_h = choose_destination_size((w, h), self.patch.image.size, self.options())
            if self.options().snap_to_patch_aspect:
                x += (w - dest_w) // 2
                y += (h - dest_h) // 2
            w, h = dest_w, dest_h
        ox, oy = self.display_offset
        scale = self.display_scale
        x1 = ox + x * scale
        y1 = oy + y * scale
        x2 = ox + (x + w) * scale
        y2 = oy + (y + h) * scale
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00e5ff", width=2)
        handle = 6
        for hx, hy in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
            self.canvas.create_rectangle(hx - handle, hy - handle, hx + handle, hy + handle, fill="#00e5ff", outline="#111")

    def canvas_to_image_point(self, event) -> Tuple[int, int]:
        ox, oy = self.display_offset
        scale = max(0.0001, self.display_scale)
        return int(round((event.x - ox) / scale)), int(round((event.y - oy) / scale))

    def hit_test(self, ix: int, iy: int) -> str:
        x, y, w, h = self.current_region()
        tolerance = max(8, int(round(10 / max(self.display_scale, 0.1))))
        points = {
            "nw": (x, y),
            "ne": (x + w, y),
            "sw": (x, y + h),
            "se": (x + w, y + h),
        }
        for name, (px, py) in points.items():
            if abs(ix - px) <= tolerance and abs(iy - py) <= tolerance:
                return name
        if x <= ix <= x + w and y <= iy <= y + h:
            return "move"
        return "new"

    def on_pointer_down(self, event):
        if not self.base:
            return
        ix, iy = self.canvas_to_image_point(event)
        self.drag_mode = self.hit_test(ix, iy)
        self.drag_start = (ix, iy)
        self.drag_original = self.current_region()
        if self.drag_mode == "new":
            self.set_region(ix, iy, 1, 1)

    def on_pointer_move(self, event):
        if not self.base or not self.drag_mode:
            return
        ix, iy = self.canvas_to_image_point(event)
        sx, sy = self.drag_start
        x, y, w, h = self.drag_original
        if self.drag_mode == "move":
            self.set_region(x + ix - sx, y + iy - sy, w, h)
            return
        if self.drag_mode == "new":
            self.set_region(sx, sy, ix - sx, iy - sy)
            return
        left, top, right, bottom = x, y, x + w, y + h
        if "n" in self.drag_mode:
            top = iy
        if "s" in self.drag_mode:
            bottom = iy
        if "w" in self.drag_mode:
            left = ix
        if "e" in self.drag_mode:
            right = ix
        self.set_region(left, top, right - left, bottom - top)

    def on_pointer_up(self, _event):
        self.drag_mode = None

    def save_png(self):
        if not (self.base and self.patch):
            self.status_var.set("Load both images before saving.")
            return
        from tkinter import filedialog, messagebox

        default = f"{self.base.path.stem}_composited.png"
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default,
            filetypes=(("PNG image", "*.png"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            result = composite_images(self.base.image, self.patch.image, self.current_region(), self.options())
            result.save(path)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.status_var.set(f"Saved: {path}")


def run_gui(argv: Optional[Sequence[str]] = None) -> int:
    configure_tcl_tk_paths()
    import tkinter as tk

    root = tk.Tk()
    app = RegionCompositorApp(root)
    args = list(argv or [])
    if len(args) >= 1:
        base = Path(args[0])
        if base.exists():
            app.load_base(base)
    if len(args) >= 2:
        patch = Path(args[1])
        if patch.exists():
            app.load_patch(patch)
    root.mainloop()
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Composite a patch image onto a selected region of a base image.")
    parser.add_argument("--base", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--x", type=int, default=0)
    parser.add_argument("--y", type=int, default=0)
    parser.add_argument("--w", type=positive_int, default=512)
    parser.add_argument("--h", type=positive_int, default=512)
    parser.add_argument("--size-source", choices=("selection", "patch", "custom"), default="selection")
    parser.add_argument("--custom-width", type=positive_int, default=512)
    parser.add_argument("--custom-height", type=positive_int, default=512)
    parser.add_argument("--scale-percent", type=float, default=100.0)
    parser.add_argument("--fit-mode", choices=("stretch", "contain", "cover"), default="stretch")
    parser.add_argument("--no-auto-resize", action="store_true")
    parser.add_argument("--snap-aspect", action="store_true")
    parser.add_argument("--no-black-to-alpha", action="store_true")
    parser.add_argument("--black-threshold", type=int, default=18)
    parser.add_argument("--black-softness", type=int, default=18)
    parser.add_argument("--feather", type=int, default=1)
    parser.add_argument("--opacity", type=float, default=100.0)
    parser.add_argument("gui_paths", nargs="*")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    cli_mode = bool(args.base or args.patch or args.out)
    if not cli_mode:
        try:
            return run_gui(args.gui_paths)
        except ModuleNotFoundError as exc:
            if exc.name == "tkinter":
                print("tkinter is not available in this Python. Use a full Python install or the packaged exe.", file=sys.stderr)
                return 2
            raise

    if not (args.base and args.patch and args.out):
        raise SystemExit("--base, --patch, and --out are required for CLI compositing")
    base = Image.open(args.base).convert("RGBA")
    patch = Image.open(args.patch).convert("RGBA")
    options = CompositeOptions(
        auto_resize=not args.no_auto_resize,
        fit_mode=args.fit_mode,
        size_source=args.size_source,
        custom_size=(args.custom_width, args.custom_height),
        scale_percent=args.scale_percent,
        snap_to_patch_aspect=args.snap_aspect,
        black_to_alpha=not args.no_black_to_alpha,
        black_threshold=args.black_threshold,
        black_softness=args.black_softness,
        feather=args.feather,
        opacity=max(0.0, min(1.0, args.opacity / 100.0)),
    )
    result = composite_images(base, patch, (args.x, args.y, args.w, args.h), options)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.out)
    print(f"saved {args.out} ({result.width}x{result.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
