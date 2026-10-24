# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
VENDOR_DIR = APP_DIR / "vendor"
try:
    if any((VENDOR_DIR / package / "__init__.py").is_file() for package in ("PIL", "tkinterdnd2")):
        sys.path.insert(0, str(VENDOR_DIR))
except OSError:
    pass

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except (ImportError, ModuleNotFoundError, PermissionError):
    DND_FILES = None
    TkinterDnD = None

try:
    from PIL import Image, ImageChops, ImageDraw, ImageStat, ImageTk
except ModuleNotFoundError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Pillow가 필요합니다",
        "이 프로그램은 이미지 처리를 위해 Pillow가 필요합니다.\n\n"
        "설치 명령:\npy -3 -m pip install pillow",
    )
    raise SystemExit(1)


RESAMPLE = Image.Resampling.LANCZOS
MIN_REGION = 0.01


@dataclass
class LoadedImage:
    path: Path
    image: Image.Image

    @property
    def label(self) -> str:
        width, height = self.image.size
        return f"{self.path.name}  {width}x{height}"


class RegionCompositorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("이미지 구역 합성기")
        self.root.geometry("1180x760")
        self.root.minsize(920, 580)

        self.base: LoadedImage | None = None
        self.patch: LoadedImage | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.preview_metrics = (1.0, 0.0, 0.0, 1.0, 1.0)
        self.drag_mode: str | None = None
        self.drag_start_point: tuple[float, float] | None = None
        self.drag_start_rect: tuple[float, float, float, float] | None = None
        self._syncing_controls = False

        self.rect = [0.25, 0.25, 0.50, 0.50]
        self.view_mode = tk.StringVar(value="composite")
        self.show_guide = tk.BooleanVar(value=True)
        self.lock_aspect = tk.BooleanVar(value=True)
        self.edge_match = tk.BooleanVar(value=True)

        self.x_var = tk.DoubleVar(value=25.0)
        self.y_var = tk.DoubleVar(value=25.0)
        self.w_var = tk.DoubleVar(value=50.0)
        self.h_var = tk.DoubleVar(value=50.0)
        self.opacity_var = tk.DoubleVar(value=100.0)
        self.feather_var = tk.DoubleVar(value=24.0)

        self.x_text = tk.StringVar(value="25.0%")
        self.y_text = tk.StringVar(value="25.0%")
        self.w_text = tk.StringVar(value="50.0%")
        self.h_text = tk.StringVar(value="50.0%")
        self.opacity_text = tk.StringVar(value="100%")
        self.feather_text = tk.StringVar(value="24px")
        self.base_text = tk.StringVar(value="비어 있음")
        self.patch_text = tk.StringVar(value="비어 있음")
        self.status_text = tk.StringVar(value="기준 이미지와 합성 이미지를 불러오세요.")
        self.drop_available = DND_FILES is not None

        self._configure_style()
        self._build_ui()
        self._bind_events()
        self.render()
        self._setup_drop_targets()

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("App.TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("Title.TLabel", background="#f4f6f8", foreground="#1f2328", font=("Malgun Gothic", 21, "bold"))
        style.configure("Hint.TLabel", background="#f4f6f8", foreground="#0f766e", font=("Malgun Gothic", 9, "bold"))
        style.configure("Panel.TLabel", background="#ffffff", foreground="#1f2328", font=("Malgun Gothic", 10))
        style.configure("Meta.TLabel", background="#ffffff", foreground="#65717f", font=("Malgun Gothic", 9))
        style.configure("TButton", font=("Malgun Gothic", 10))
        style.configure("Primary.TButton", font=("Malgun Gothic", 10, "bold"))
        style.configure("TRadiobutton", background="#ffffff", foreground="#1f2328", font=("Malgun Gothic", 10))
        style.configure("TCheckbutton", background="#ffffff", foreground="#1f2328", font=("Malgun Gothic", 10))

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.configure(background="#f4f6f8")

        header = ttk.Frame(self.root, style="App.TFrame", padding=(18, 14, 18, 8))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="REGION IMAGE COMPOSITOR", style="Hint.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="이미지 구역 합성기", style="Title.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Button(header, text="기준/합성 바꾸기", command=self.swap_images).grid(row=0, column=1, rowspan=2, padx=(8, 8), sticky="e")
        ttk.Button(header, text="기준 파일 덮어쓰기", style="Primary.TButton", command=self.save_png).grid(row=0, column=2, rowspan=2, sticky="e")

        panel = ttk.Frame(self.root, style="Panel.TFrame", padding=14)
        panel.grid(row=1, column=0, sticky="nsw", padx=(18, 8), pady=(6, 18))
        panel.columnconfigure(0, weight=1)

        self._build_upload_section(panel)
        self._build_mode_section(panel)
        self._build_region_section(panel)
        self._build_blend_section(panel)
        self._build_toggle_section(panel)

        canvas_frame = ttk.Frame(self.root, style="App.TFrame", padding=(0, 6, 18, 18))
        canvas_frame.grid(row=1, column=1, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#eef2f4", highlightthickness=1, highlightbackground="#d9dee5", cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ttk.Label(canvas_frame, textvariable=self.status_text, style="Hint.TLabel").grid(row=1, column=0, sticky="ew", pady=(8, 0))

    def _build_upload_section(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="이미지", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.base_button = ttk.Button(parent, text="기준 이미지 열기", command=self.open_base)
        self.base_button.grid(row=1, column=0, sticky="ew", pady=(8, 3))
        self.base_label = ttk.Label(parent, textvariable=self.base_text, style="Meta.TLabel", wraplength=300)
        self.base_label.grid(row=2, column=0, sticky="ew")
        self.patch_button = ttk.Button(parent, text="합성 이미지 열기", command=self.open_patch)
        self.patch_button.grid(row=3, column=0, sticky="ew", pady=(12, 3))
        self.patch_label = ttk.Label(parent, textvariable=self.patch_text, style="Meta.TLabel", wraplength=300)
        self.patch_label.grid(row=4, column=0, sticky="ew")

    def _build_mode_section(self, parent: ttk.Frame) -> None:
        group = ttk.Frame(parent, style="Panel.TFrame")
        group.grid(row=5, column=0, sticky="ew", pady=(20, 6))
        for index, (text, value) in enumerate((("합성", "composite"), ("기준", "base"), ("합성본", "patch"))):
            group.columnconfigure(index, weight=1)
            ttk.Radiobutton(
                group,
                text=text,
                value=value,
                variable=self.view_mode,
                command=self.render,
            ).grid(row=0, column=index, sticky="w")

    def _build_region_section(self, parent: ttk.Frame) -> None:
        region = ttk.Frame(parent, style="Panel.TFrame")
        region.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        region.columnconfigure(1, weight=1)
        controls = (
            ("X", self.x_var, self.x_text, "x"),
            ("Y", self.y_var, self.y_text, "y"),
            ("W", self.w_var, self.w_text, "w"),
            ("H", self.h_var, self.h_text, "h"),
        )
        for row, (label, var, text_var, key) in enumerate(controls):
            ttk.Label(region, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=5)
            scale = ttk.Scale(region, from_=0.0 if key in ("x", "y") else 1.0, to=100.0, variable=var, command=lambda _v, k=key: self.update_rect_from_controls(k))
            scale.grid(row=row, column=1, sticky="ew", padx=8)
            ttk.Label(region, textvariable=text_var, style="Meta.TLabel", width=8, anchor="e").grid(row=row, column=2, sticky="e")

    def _build_blend_section(self, parent: ttk.Frame) -> None:
        blend = ttk.Frame(parent, style="Panel.TFrame")
        blend.grid(row=7, column=0, sticky="ew", pady=(18, 0))
        blend.columnconfigure(1, weight=1)
        rows = (
            ("불투명도", self.opacity_var, self.opacity_text, self.update_blend),
            ("페더", self.feather_var, self.feather_text, self.update_blend),
        )
        for row, (label, var, text_var, command) in enumerate(rows):
            ttk.Label(blend, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=5)
            to_value = 100.0 if row == 0 else 200.0
            ttk.Scale(blend, from_=0.0, to=to_value, variable=var, command=lambda _v, c=command: c()).grid(row=row, column=1, sticky="ew", padx=8)
            ttk.Label(blend, textvariable=text_var, style="Meta.TLabel", width=8, anchor="e").grid(row=row, column=2, sticky="e")

    def _build_toggle_section(self, parent: ttk.Frame) -> None:
        toggles = ttk.Frame(parent, style="Panel.TFrame")
        toggles.grid(row=8, column=0, sticky="ew", pady=(18, 0))
        ttk.Checkbutton(toggles, text="선택 영역 표시", variable=self.show_guide, command=self.render).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(toggles, text="비율 잠금", variable=self.lock_aspect).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(toggles, text="경계 색 보정", variable=self.edge_match, command=self.render).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _bind_events(self) -> None:
        self.canvas.bind("<Configure>", lambda _event: self.render())
        self.canvas.bind("<ButtonPress-1>", self.on_pointer_down)
        self.canvas.bind("<B1-Motion>", self.on_pointer_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_pointer_up)

    def _setup_drop_targets(self) -> None:
        if not self.drop_available:
            self.status_text.set("드래그앤드롭을 쓰려면 tkinterdnd2가 필요합니다. 버튼 클릭으로는 그대로 열 수 있습니다.")
            return
        self._register_drop_target(self.base_button, "base")
        self._register_drop_target(self.base_label, "base")
        self._register_drop_target(self.patch_button, "patch")
        self._register_drop_target(self.patch_label, "patch")

    def _register_drop_target(self, widget: tk.Widget, target: str) -> None:
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", lambda event, key=target: self.handle_file_drop(event, key))

    def handle_file_drop(self, event: tk.Event, target: str) -> str:
        paths = self.parse_drop_paths(getattr(event, "data", ""))
        image_path = next((path for path in paths if self.is_supported_image(path)), None)
        if image_path is None:
            messagebox.showinfo("이미지 파일이 없습니다", "PNG, JPG, WEBP, BMP, TIFF 이미지를 놓아주세요.")
            return "break"
        self.load_image_path(image_path, target)
        return "break"

    def parse_drop_paths(self, data: str) -> list[Path]:
        if not data:
            return []
        try:
            values = self.root.tk.splitlist(data)
        except tk.TclError:
            values = [data]
        return [Path(value.strip()) for value in values if value.strip()]

    @staticmethod
    def is_supported_image(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

    def open_base(self) -> None:
        loaded = self._open_image_dialog("기준 이미지 열기")
        if not loaded:
            return
        self.base = loaded
        self.base_text.set(loaded.label)
        self.render()

    def open_patch(self) -> None:
        loaded = self._open_image_dialog("합성 이미지 열기")
        if not loaded:
            return
        self.patch = loaded
        self.patch_text.set(loaded.label)
        self.render()

    def load_image_path(self, path: Path, target: str) -> None:
        try:
            loaded = self._load_image(path)
        except Exception as exc:
            messagebox.showerror("이미지 열기 실패", f"이미지를 열 수 없습니다.\n\n{exc}")
            return
        if target == "base":
            self.base = loaded
            self.base_text.set(loaded.label)
        else:
            self.patch = loaded
            self.patch_text.set(loaded.label)
        self.status_text.set(f"{'기준' if target == 'base' else '합성'} 이미지 로드: {loaded.path}")
        self.render()

    def _open_image_dialog(self, title: str) -> LoadedImage | None:
        path = filedialog.askopenfilename(
            title=title,
            filetypes=(
                ("이미지 파일", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
                ("모든 파일", "*.*"),
            ),
        )
        if not path:
            return None
        try:
            return self._load_image(Path(path))
        except Exception as exc:
            messagebox.showerror("이미지 열기 실패", f"이미지를 열 수 없습니다.\n\n{exc}")
            return None

    @staticmethod
    def _load_image(path: Path) -> LoadedImage:
        return LoadedImage(path, Image.open(path).convert("RGBA"))

    def swap_images(self) -> None:
        self.base, self.patch = self.patch, self.base
        self.base_text.set(self.base.label if self.base else "비어 있음")
        self.patch_text.set(self.patch.label if self.patch else "비어 있음")
        self.render()

    def update_blend(self) -> None:
        self.opacity_text.set(f"{round(self.opacity_var.get())}%")
        self.feather_text.set(f"{round(self.feather_var.get())}px")
        self.render()

    def update_rect_from_controls(self, changed: str) -> None:
        if self._syncing_controls:
            return
        old_x, old_y, old_w, old_h = self.rect
        x = self.x_var.get() / 100.0
        y = self.y_var.get() / 100.0
        w = self.w_var.get() / 100.0
        h = self.h_var.get() / 100.0

        if self.lock_aspect.get() and changed in ("w", "h") and old_w > 0 and old_h > 0:
            ratio = old_w / old_h
            if changed == "w":
                h = w / ratio
            else:
                w = h * ratio

        self.set_rect(x, y, w, h)

    def set_rect(self, x: float, y: float, w: float, h: float, render: bool = True) -> None:
        w = self._clamp(w, MIN_REGION, 1.0)
        h = self._clamp(h, MIN_REGION, 1.0)
        x = self._clamp(x, 0.0, 1.0 - w)
        y = self._clamp(y, 0.0, 1.0 - h)
        self.rect = [x, y, w, h]
        self.sync_controls()
        if render:
            self.render()

    def sync_controls(self) -> None:
        self._syncing_controls = True
        x, y, w, h = self.rect
        self.x_var.set(x * 100.0)
        self.y_var.set(y * 100.0)
        self.w_var.set(w * 100.0)
        self.h_var.set(h * 100.0)
        self.x_text.set(f"{x * 100.0:.1f}%")
        self.y_text.set(f"{y * 100.0:.1f}%")
        self.w_text.set(f"{w * 100.0:.1f}%")
        self.h_text.set(f"{h * 100.0:.1f}%")
        self.opacity_text.set(f"{round(self.opacity_var.get())}%")
        self.feather_text.set(f"{round(self.feather_var.get())}px")
        self._syncing_controls = False

    def render(self) -> None:
        self.sync_controls()
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        self._draw_checkerboard(width, height)

        if not self.base:
            self.status_text.set("기준 이미지와 합성 이미지를 불러오세요.")
            return

        preview = self.compose(mode=self.view_mode.get())
        if preview is None:
            return

        img_w, img_h = preview.size
        scale = min(width / img_w, height / img_h)
        display_w = max(1, round(img_w * scale))
        display_h = max(1, round(img_h * scale))
        offset_x = (width - display_w) / 2
        offset_y = (height - display_h) / 2
        self.preview_metrics = (scale, offset_x, offset_y, display_w, display_h)

        display = preview.resize((display_w, display_h), RESAMPLE)
        self.preview_photo = ImageTk.PhotoImage(display)
        self.canvas.create_image(offset_x, offset_y, anchor="nw", image=self.preview_photo)

        if self.show_guide.get():
            self.draw_canvas_guide()

        base_size = f"{self.base.image.width}x{self.base.image.height}"
        patch_size = f"{self.patch.image.width}x{self.patch.image.height}" if self.patch else "대기"
        self.status_text.set(f"기준 {base_size} / 합성 {patch_size} / 출력 {base_size}")

    def _draw_checkerboard(self, width: int, height: int) -> None:
        tile = 18
        colors = ("#f8fafc", "#e1e6ea")
        for y in range(0, height, tile):
            for x in range(0, width, tile):
                index = ((x // tile) + (y // tile)) % 2
                self.canvas.create_rectangle(x, y, x + tile, y + tile, fill=colors[index], width=0)

    def draw_canvas_guide(self) -> None:
        _scale, ox, oy, dw, dh = self.preview_metrics
        x, y, w, h = self.rect
        left = ox + x * dw
        top = oy + y * dh
        right = left + w * dw
        bottom = top + h * dh
        self.canvas.create_rectangle(left, top, right, bottom, outline="#f97316", width=2, dash=(8, 5))
        handle = 8
        for hx, hy in ((left, top), (right, top), (left, bottom), (right, bottom)):
            self.canvas.create_rectangle(hx - handle / 2, hy - handle / 2, hx + handle / 2, hy + handle / 2, fill="#f97316", outline="")

    def compose(self, mode: str = "composite") -> Image.Image | None:
        if not self.base:
            return None
        base = self.base.image.copy()
        if mode == "base" or not self.patch:
            return base

        if mode == "patch":
            return self.patch.image.resize(base.size, RESAMPLE)

        output = base.copy()
        x, y, w, h = self.rect
        bx1 = round(x * base.width)
        by1 = round(y * base.height)
        bx2 = round((x + w) * base.width)
        by2 = round((y + h) * base.height)
        bx1, by1, bx2, by2 = self._valid_box(bx1, by1, bx2, by2, base.width, base.height)
        out_w = bx2 - bx1
        out_h = by2 - by1

        patch = self.patch.image
        px1 = round(x * patch.width)
        py1 = round(y * patch.height)
        px2 = round((x + w) * patch.width)
        py2 = round((y + h) * patch.height)
        px1, py1, px2, py2 = self._valid_box(px1, py1, px2, py2, patch.width, patch.height)

        patch_crop = patch.crop((px1, py1, px2, py2)).resize((out_w, out_h), RESAMPLE)
        if self.edge_match_enabled():
            patch_crop = self.match_patch_edge_to_base(base, patch_crop, (bx1, by1, bx2, by2))
        mask = self.build_mask((out_w, out_h))
        source_alpha = patch_crop.getchannel("A")
        mask = ImageChops.multiply(source_alpha, mask)
        output.paste(patch_crop, (bx1, by1), mask)
        return output

    def build_mask(self, size: tuple[int, int]) -> Image.Image:
        width, height = size
        opacity = self._clamp(self.opacity_var.get() / 100.0, 0.0, 1.0)
        feather = round(self.feather_var.get())
        feather = max(0, min(feather, width // 2, height // 2))

        if feather == 0:
            value = round(255 * opacity)
            return Image.new("L", size, value)

        horizontal = Image.new("L", (width, 1))
        horizontal.putdata([self.edge_fade_value(min(x, width - 1 - x), feather) for x in range(width)])
        horizontal = horizontal.resize(size)

        vertical = Image.new("L", (1, height))
        vertical.putdata([self.edge_fade_value(min(y, height - 1 - y), feather) for y in range(height)])
        vertical = vertical.resize(size)

        mask = ImageChops.multiply(horizontal, vertical)
        if opacity < 1.0:
            mask = mask.point(lambda px: round(px * opacity))
        return mask

    def edge_match_enabled(self) -> bool:
        edge_match = getattr(self, "edge_match", None)
        return bool(edge_match.get()) if edge_match is not None else False

    def match_patch_edge_to_base(self, base: Image.Image, patch_crop: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
        width, height = patch_crop.size
        sample = max(3, round(self.feather_var.get() * 0.5))
        sample = min(sample, width // 2, height // 2)
        if sample <= 0:
            return patch_crop

        edge_mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(edge_mask)
        draw.rectangle((0, 0, width - 1, height - 1), fill=255)
        if width > sample * 2 and height > sample * 2:
            draw.rectangle((sample, sample, width - sample - 1, height - sample - 1), fill=0)
        edge_mask = ImageChops.multiply(edge_mask, patch_crop.getchannel("A"))

        base_crop = base.crop(box).resize((width, height), RESAMPLE)
        try:
            base_mean = ImageStat.Stat(base_crop.convert("RGB"), edge_mask).mean
            patch_mean = ImageStat.Stat(patch_crop.convert("RGB"), edge_mask).mean
        except ZeroDivisionError:
            return patch_crop
        if len(base_mean) < 3 or len(patch_mean) < 3:
            return patch_crop

        strength = 0.78
        deltas = [(base_mean[i] - patch_mean[i]) * strength for i in range(3)]
        if max(abs(delta) for delta in deltas) < 0.5:
            return patch_crop

        channels = patch_crop.split()
        adjusted_rgb = [
            channels[index].point(lambda value, delta=delta: round(self._clamp(value + delta, 0, 255)))
            for index, delta in enumerate(deltas)
        ]
        return Image.merge("RGBA", (*adjusted_rgb, channels[3]))

    @staticmethod
    def edge_fade_value(distance: int, feather: int) -> int:
        if feather <= 0:
            return 255
        t = min(max(distance / feather, 0.0), 1.0)
        t = t * t * (3.0 - 2.0 * t)
        return round(255 * t)

    def save_png(self) -> None:
        if not self.base:
            messagebox.showinfo("저장할 이미지가 없습니다", "먼저 기준 이미지를 불러오세요.")
            return
        if not self.patch:
            messagebox.showinfo("합성 이미지가 없습니다", "먼저 합성 이미지를 불러오세요.")
            return

        path = self.base.path
        confirmed = messagebox.askyesno(
            "기준 이미지 덮어쓰기",
            f"합성 결과를 기준 이미지와 같은 이름으로 저장하고 기존 파일을 대체합니다.\n\n{path}\n\n계속할까요?",
        )
        if not confirmed:
            return
        try:
            output = self.compose(mode="composite")
            if output is None:
                return
            self.save_image_replacing(output, path)
            self.base = LoadedImage(path, Image.open(path).convert("RGBA"))
            self.base_text.set(self.base.label)
            self.status_text.set(f"덮어쓰기 완료: {path}")
        except Exception as exc:
            messagebox.showerror("저장 실패", f"이미지를 덮어쓸 수 없습니다.\n\n{exc}")

    def save_image_replacing(self, image: Image.Image, path: Path) -> None:
        suffix = path.suffix.lower()
        temp_path = path.with_name(f"{path.stem}.tmp{suffix or '.png'}")
        save_kwargs = {}
        output = image

        if suffix in (".jpg", ".jpeg"):
            output = self.flatten_for_rgb(image)
            image_format = "JPEG"
            save_kwargs.update(quality=95, subsampling=0)
        elif suffix == ".webp":
            image_format = "WEBP"
            save_kwargs.update(quality=100, lossless=True)
        elif suffix == ".bmp":
            output = self.flatten_for_rgb(image)
            image_format = "BMP"
        elif suffix in (".tif", ".tiff"):
            image_format = "TIFF"
        else:
            image_format = "PNG"
            if suffix != ".png":
                temp_path = path.with_name(f"{path.name}.tmp.png")

        output.save(temp_path, image_format, **save_kwargs)
        temp_path.replace(path)

    @staticmethod
    def flatten_for_rgb(image: Image.Image) -> Image.Image:
        if image.mode == "RGB":
            return image
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "RGBA":
            background.paste(image, mask=image.getchannel("A"))
        else:
            background.paste(image.convert("RGB"))
        return background

    def on_pointer_down(self, event: tk.Event) -> None:
        if not self.base:
            return
        point = self.canvas_point_to_percent(event.x, event.y)
        self.drag_mode = self.hit_test(point)
        self.drag_start_point = point
        self.drag_start_rect = tuple(self.rect)

    def on_pointer_move(self, event: tk.Event) -> None:
        if not self.drag_mode or not self.drag_start_point or not self.drag_start_rect:
            return
        point = self.canvas_point_to_percent(event.x, event.y)
        sx, sy = self.drag_start_point
        rx, ry, rw, rh = self.drag_start_rect
        dx = point[0] - sx
        dy = point[1] - sy

        if self.drag_mode == "move":
            self.set_rect(rx + dx, ry + dy, rw, rh)
            return

        if self.drag_mode.startswith("resize_"):
            self.resize_from_corner(self.drag_mode, point, dx, dy)
            return

        left = min(sx, point[0])
        top = min(sy, point[1])
        width = max(MIN_REGION, abs(point[0] - sx))
        height = max(MIN_REGION, abs(point[1] - sy))
        if self.lock_aspect.get():
            ratio = self.drag_start_rect[2] / max(MIN_REGION, self.drag_start_rect[3])
            height = width / ratio
        self.set_rect(left, top, width, height)

    def on_pointer_up(self, _event: tk.Event) -> None:
        self.drag_mode = None
        self.drag_start_point = None
        self.drag_start_rect = None

    def resize_from_corner(self, mode: str, point: tuple[float, float], dx: float, dy: float) -> None:
        if not self.drag_start_rect:
            return
        rx, ry, rw, rh = self.drag_start_rect
        left, top, right, bottom = rx, ry, rx + rw, ry + rh
        west = mode.endswith("nw") or mode.endswith("sw")
        north = mode.endswith("nw") or mode.endswith("ne")
        fixed_x = right if west else left
        fixed_y = bottom if north else top

        new_w = max(MIN_REGION, abs(point[0] - fixed_x))
        new_h = max(MIN_REGION, abs(point[1] - fixed_y))

        if self.lock_aspect.get() and rw > 0 and rh > 0:
            ratio = rw / rh
            if abs(dx) >= abs(dy):
                new_h = new_w / ratio
            else:
                new_w = new_h * ratio

        new_x = fixed_x - new_w if west else fixed_x
        new_y = fixed_y - new_h if north else fixed_y
        self.set_rect(new_x, new_y, new_w, new_h)

    def canvas_point_to_percent(self, x: float, y: float) -> tuple[float, float]:
        _scale, ox, oy, dw, dh = self.preview_metrics
        px = (x - ox) / dw
        py = (y - oy) / dh
        return self._clamp(px, 0.0, 1.0), self._clamp(py, 0.0, 1.0)

    def hit_test(self, point: tuple[float, float]) -> str:
        _scale, _ox, _oy, dw, dh = self.preview_metrics
        x, y, w, h = self.rect
        px, py = point
        threshold_x = max(0.012, 14.0 / max(1.0, dw))
        threshold_y = max(0.012, 14.0 / max(1.0, dh))
        near_left = abs(px - x) <= threshold_x
        near_right = abs(px - (x + w)) <= threshold_x
        near_top = abs(py - y) <= threshold_y
        near_bottom = abs(py - (y + h)) <= threshold_y
        inside = x <= px <= x + w and y <= py <= y + h
        if near_left and near_top:
            return "resize_nw"
        if near_right and near_top:
            return "resize_ne"
        if near_left and near_bottom:
            return "resize_sw"
        if near_right and near_bottom:
            return "resize_se"
        if inside:
            return "move"
        return "create"

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        if high < low:
            return low
        return min(max(value, low), high)

    @staticmethod
    def _valid_box(x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> tuple[int, int, int, int]:
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(x1 + 1, min(x2, width))
        y2 = max(y1 + 1, min(y2, height))
        return x1, y1, x2, y2


def main() -> int:
    if TkinterDnD is not None:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    RegionCompositorApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
