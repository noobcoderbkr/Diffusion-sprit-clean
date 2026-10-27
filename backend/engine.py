"""Headless Pillow compositor, retained from ff7de566.

The original desktop UI was removed. Pixel-output regression baselines are
stored in tests/compositing_baselines.json, captured before UI removal.
"""
from PIL import Image, ImageChops, ImageDraw, ImageStat
from types import SimpleNamespace
RESAMPLE = Image.Resampling.LANCZOS

class Value:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value

class Compositor:
    def __init__(self, base, patch, rect, opacity, feather, edge_match):
        self.base = SimpleNamespace(image=base)
        self.patch = SimpleNamespace(image=patch) if patch is not None else None
        self.rect = rect
        self.opacity_var = Value(opacity)
        self.feather_var = Value(feather)
        self.edge_match = Value(edge_match)

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
