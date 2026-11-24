"""Reads one PDF into per-page model input. Text layer: pypdf layout-mode text (keeps two-column rows apart).
No text layer: the page image (embedded raster, else rendered with pypdfium2). Records which input was used."""
import base64
import io

from pypdf import PdfReader

MIN_TEXT_CHARS = 20  # fewer non-space characters than this on a page counts as "no text layer"


def read_pages(pdf_path):
    """[{page, mode: 'layout_text'|'image', text, image_b64, media_type, chars}] for each page."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for n, page in enumerate(reader.pages, start=1):
        text = page.extract_text(extraction_mode="layout") or ""
        chars = len("".join(text.split()))
        if chars >= MIN_TEXT_CHARS:
            pages.append({"page": n, "mode": "layout_text", "text": text, "chars": chars})
            continue
        data, media = _page_image(pdf_path, reader, page, n)
        pages.append({"page": n, "mode": "image", "image_b64": base64.b64encode(data).decode("ascii"),
                      "media_type": media, "chars": chars})
    return pages


def _page_image(pdf_path, reader, page, n):
    imgs = list(page.images)
    if imgs:
        im = imgs[0]
        name = (im.name or "").lower()
        media = "image/png" if name.endswith("png") else "image/jpeg" if name.endswith(("jpg", "jpeg")) else None
        if media:
            return im.data, media
        buf = io.BytesIO()
        im.image.convert("RGB").save(buf, "PNG")
        return buf.getvalue(), "image/png"
    import pypdfium2  # fallback: render the page
    pdf = pypdfium2.PdfDocument(str(pdf_path))
    buf = io.BytesIO()
    pdf[n - 1].render(scale=2.0).to_pil().convert("RGB").save(buf, "PNG")
    return buf.getvalue(), "image/png"
