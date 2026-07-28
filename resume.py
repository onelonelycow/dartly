"""
resume.py — pull plain text out of an uploaded resume. In memory only.

Nothing here ever touches disk or the database. The extracted text lives in
Streamlit's session state (see view_profile() in app.py) for exactly as long
as the browser tab stays open, then it's gone — the founder's own words were
"make it so we're not tracking their personal information." The one honest
exception: the text IS sent to Anthropic to draft a reply, once, when the
person asks for one. That's disclosed in the privacy policy (legal.py), same
commit as this file.
"""
import io
import re

MAX_CHARS = 6000   # roughly two pages — enough signal, keeps the prompt cheap
# Belt and suspenders on top of .streamlit/config.toml's server-level
# maxUploadSize=10. That config caps what the browser can even SEND; this caps
# what this function will bother to PARSE, so a future caller that skips the
# config (a different entry point, a test harness) still can't hand pypdf a
# huge byte string on a small instance.
MAX_BYTES = 10 * 1024 * 1024


def extract_text(uploaded_file) -> str:
    """
    Best-effort plain text from a Streamlit UploadedFile.

    '' on anything unreadable OR too large (a scanned/image-only PDF, a
    corrupt file, something oversized) — callers should treat that as
    "nothing changed" and let drafting continue without it, never as an
    error that blocks the feature.
    """
    name = (uploaded_file.name or "").lower()
    try:
        data = uploaded_file.getvalue()
        if len(data) > MAX_BYTES:
            return ""
        text = _from_pdf(data) if name.endswith(".pdf") else data.decode(
            "utf-8", errors="ignore")
    except Exception:
        return ""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CHARS]


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
