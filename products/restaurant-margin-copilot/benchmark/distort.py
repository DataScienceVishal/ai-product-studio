"""Phone-photo distortion with Pillow and numpy only: crumple, rotation, perspective, uneven light, shadow, blur, noise, JPEG."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter


def _smooth_field(rng: np.random.Generator, h: int, w: int, grid: tuple[int, int], amp: float) -> np.ndarray:
    small = rng.normal(0.0, 1.0, grid).astype(np.float32)
    img = Image.fromarray(small, mode="F").resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) * amp


def _warp(arr: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sx = np.clip(xx + dx, 0, w - 1)
    sy = np.clip(yy + dy, 0, h - 1)
    x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    top = arr[y0, x0] * (1 - fx) + arr[y0, x1] * fx
    bot = arr[y1, x0] * (1 - fx) + arr[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def _perspective_coeffs(dst_quad, src_quad):
    """Coefficients for Image.transform(PERSPECTIVE): maps each output point (dst) to an input point (src)."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst_quad, src_quad):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        rhs += [u, v]
    return np.linalg.solve(np.array(rows, dtype=np.float64), np.array(rhs, dtype=np.float64)).tolist()


def make_photo(page: Image.Image, seed: int, max_side: int = 2000) -> tuple[bytes, dict]:
    """(JPEG bytes, parameters used) of the page as if photographed on a desk with a phone."""
    rng = np.random.default_rng(seed)
    params: dict = {"seed": seed}
    page = page.convert("RGB")
    w, h = page.size
    arr = np.asarray(page, dtype=np.float32)

    # crumple: slow warp plus soft crease shading
    params["crumple_amp_px"] = round(float(rng.uniform(2.0, 5.0)), 2)
    arr = _warp(arr, _smooth_field(rng, h, w, (7, 5), params["crumple_amp_px"]),
                _smooth_field(rng, h, w, (7, 5), params["crumple_amp_px"]))
    crease = _smooth_field(rng, h, w, (14, 10), 1.0)
    arr *= (1.0 + 0.035 * crease)[..., None]
    arr = np.clip(arr, 0, 255)
    paper = Image.fromarray(arr.astype(np.uint8))

    # desk background, bigger than the page so rotation and skew keep it in frame
    pad = int(0.12 * max(w, h))
    cw, ch = w + 2 * pad, h + 2 * pad
    desk = np.array([rng.integers(70, 150), rng.integers(55, 120), rng.integers(40, 100)], dtype=np.float32)
    bg = np.ones((ch, cw, 3), dtype=np.float32) * desk
    bg *= (1.0 + 0.08 * _smooth_field(rng, ch, cw, (6, 6), 1.0))[..., None]
    canvas = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    canvas.paste(paper, (pad, pad))

    # rotation 2-8 degrees either way
    angle = float(rng.uniform(2.0, 12.0) * rng.choice([-1, 1]))
    params["rotation_deg"] = round(angle, 2)
    canvas = canvas.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=tuple(int(c) for c in desk))

    # perspective: move each corner inwards or outwards by up to 5% of the size
    j = float(rng.uniform(0.02, 0.06))
    params["perspective_jitter"] = round(j, 3)
    cwf, chf = float(cw), float(ch)
    src = [(rng.uniform(-j, j) * cwf, rng.uniform(-j, j) * chf),
           (cwf + rng.uniform(-j, j) * cwf, rng.uniform(-j, j) * chf),
           (cwf + rng.uniform(-j, j) * cwf, chf + rng.uniform(-j, j) * chf),
           (rng.uniform(-j, j) * cwf, chf + rng.uniform(-j, j) * chf)]
    dst = [(0, 0), (cwf, 0), (cwf, chf), (0, chf)]
    canvas = canvas.transform((cw, ch), Image.PERSPECTIVE, _perspective_coeffs(dst, src), Image.BICUBIC)

    # crop towards the page, with a little desk showing
    m = int(pad * rng.uniform(0.2, 0.6))
    canvas = canvas.crop((m, m, cw - m, ch - m))
    cw, ch = canvas.size
    arr = np.asarray(canvas, dtype=np.float32)

    # uneven light: a linear gradient plus a soft diagonal shadow
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    theta = rng.uniform(0, 2 * np.pi)
    g = (np.cos(theta) * (xx / cw - 0.5) + np.sin(theta) * (yy / ch - 0.5))
    arr *= (1.0 + rng.uniform(0.12, 0.3) * g)[..., None]
    shadow_pos = rng.uniform(0.2, 0.8)
    d = (xx / cw) * np.cos(theta + 1.2) + (yy / ch) * np.sin(theta + 1.2)
    band = 1.0 / (1.0 + np.exp(-(d - shadow_pos) * 14.0))
    params["shadow_strength"] = round(float(rng.uniform(0.12, 0.35)), 3)
    arr *= (1.0 - params["shadow_strength"] * band)[..., None]

    # blur, sensor noise, resize, JPEG
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    params["blur_sigma"] = round(float(rng.uniform(0.5, 1.5)), 2)
    img = img.filter(ImageFilter.GaussianBlur(radius=params["blur_sigma"]))
    noisy = np.asarray(img, dtype=np.float32) + rng.normal(0, rng.uniform(3.0, 7.0), (ch, cw, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(noisy, 0, 255).astype(np.uint8))
    scale = max_side / max(img.size)
    if scale < 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    params["jpeg_quality"] = int(rng.integers(35, 71))
    img.save(buf, "JPEG", quality=params["jpeg_quality"])
    return buf.getvalue(), params
