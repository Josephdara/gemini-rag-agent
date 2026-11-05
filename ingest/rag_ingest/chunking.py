from pathlib import Path

SUFFIXES = {".md", ".txt"}


def read_documents(folder):
    """Yields (source, text) for each Markdown or text file, with source relative to the folder."""
    root = Path(folder)
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in SUFFIXES:
            yield path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")


def chunk_text(text, size=500, overlap=100):
    """Splits text into windows of about size characters, each starting overlap characters before the previous
    one ended. Windows end at whitespace where possible so words stay whole."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # Last whitespace in the second half of the window, if any.
            cut = max(text.rfind(" ", start + size // 2, end), text.rfind("\n", start + size // 2, end))
            if cut != -1:
                end = cut
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - overlap
        # Move forward to the start of a word; with no whitespace in the overlap, the next window has none.
        while start < end and not text[start - 1].isspace():
            start += 1
    return [chunk for chunk in chunks if chunk]
