#!/usr/bin/env python3
"""Fail closed when the public Sneferu site is incomplete or miswired."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ENTRY_PAGES = ("index.html", "atlas-preview.html")
REQUIRED_PATHS = ENTRY_PAGES + ("CNAME", ".nojekyll", "research")
FORBIDDEN_PATHS = (
    "atlas.html",
    "request-access.html",
    "specsrc",
    "previews",
    "tools",
)
FORM_ACTION = "https://formspree.io/f/xpqvqqra"
MAX_FILE_BYTES = 100 * 1024 * 1024
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
LOCAL_HOST = re.compile(
    r"(?:file://|https?://(?:localhost|127\.0\.0\.1|[^/'\"\s]+\.local)(?::\d+)?)",
    re.IGNORECASE,
)


@dataclass
class Document:
    path: Path
    ids: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    forms: list[dict[str, str | None]] = field(default_factory=list)
    email_inputs: list[dict[str, str | None]] = field(default_factory=list)


class Collector(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.document = Document(path=path)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.document.ids.append(values["id"] or "")

        for name in ("href", "src", "poster", "data-src"):
            if values.get(name):
                self.document.references.append(values[name] or "")

        if values.get("srcset"):
            for candidate in (values["srcset"] or "").split(","):
                url = candidate.strip().split(maxsplit=1)[0]
                if url:
                    self.document.references.append(url)

        if values.get("style"):
            self.document.references.extend(extract_css_urls(values["style"] or ""))

        if tag == "form":
            self.document.forms.append(values)
        if tag == "input" and (values.get("type") or "").lower() == "email":
            self.document.email_inputs.append(values)


def extract_css_urls(text: str) -> list[str]:
    return [match.group(2).strip() for match in CSS_URL.finditer(text) if match.group(2).strip()]


def parse_document(path: Path) -> tuple[Document, str]:
    text = path.read_text(encoding="utf-8")
    parser = Collector(path)
    parser.feed(text)
    parser.close()
    parser.document.references.extend(extract_css_urls(text))
    return parser.document, text


def local_target(root: Path, document: Path, reference: str) -> tuple[Path | None, str]:
    reference = reference.strip()
    if not reference or reference == "#":
        return None, ""

    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("//"):
        return None, ""

    fragment = unquote(parsed.fragment)
    raw_path = unquote(parsed.path)
    if not raw_path:
        return document, fragment

    if raw_path.startswith("/"):
        target = root / raw_path.lstrip("/")
    else:
        target = document.parent / raw_path
    target = target.resolve()

    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(f"reference escapes the public root: {reference}")

    if target.is_dir():
        target /= "index.html"
    return target, fragment


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.resolve()

    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            errors.append(f"missing required path: {relative}")

    if (root / "CNAME").exists() and (root / "CNAME").read_text(encoding="utf-8").strip() != "sneferu.ai":
        errors.append("CNAME must contain exactly sneferu.ai")

    for relative in FORBIDDEN_PATHS:
        if (root / relative).exists():
            errors.append(f"private working file reached the public artifact: {relative}")

    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symbolic links are not allowed in the Pages artifact: {path.relative_to(root)}")
        elif path.is_file() and path.stat().st_size >= MAX_FILE_BYTES:
            errors.append(f"file is too large for GitHub Pages: {path.relative_to(root)}")

    documents: dict[Path, Document] = {}
    texts: dict[Path, str] = {}
    for relative in ENTRY_PAGES:
        path = (root / relative).resolve()
        if not path.exists():
            continue
        try:
            document, text = parse_document(path)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot parse {relative}: {exc}")
            continue
        documents[path] = document
        texts[path] = text

        duplicates = sorted(name for name, count in Counter(document.ids).items() if count > 1)
        if duplicates:
            errors.append(f"duplicate id values in {relative}: {', '.join(duplicates)}")
        if LOCAL_HOST.search(text):
            errors.append(f"local-only URL found in {relative}")

    for path, document in list(documents.items()):
        for reference in document.references:
            try:
                target, fragment = local_target(root, path, reference)
            except ValueError as exc:
                errors.append(f"{path.relative_to(root)}: {exc}")
                continue
            if target is None:
                continue
            if not target.exists() or not target.is_file():
                errors.append(f"broken local reference in {path.relative_to(root)}: {reference}")
                continue
            if fragment and target.suffix.lower() in {".html", ".htm"}:
                target_document = documents.get(target)
                if target_document is None:
                    try:
                        target_document, _ = parse_document(target)
                        documents[target] = target_document
                    except (OSError, UnicodeError) as exc:
                        errors.append(f"cannot parse linked page {target.relative_to(root)}: {exc}")
                        continue
                if fragment not in target_document.ids:
                    errors.append(
                        f"broken anchor in {path.relative_to(root)}: {reference} "
                        f"(missing #{fragment})"
                    )

    index = documents.get((root / "index.html").resolve())
    if index is not None:
        if len(index.forms) != 1:
            errors.append(f"index.html must contain one contact form; found {len(index.forms)}")
        else:
            form = index.forms[0]
            if form.get("action") != FORM_ACTION:
                errors.append("contact form action is not the approved Formspree endpoint")
            if (form.get("method") or "").lower() != "post":
                errors.append("contact form method must be POST")
        if not any("required" in attrs and attrs.get("name") == "email" for attrs in index.email_inputs):
            errors.append("contact form must require an email address")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()

    errors = validate(root)
    if errors:
        print("Site validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    files = [path for path in root.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    print(f"Site validation passed: {len(files)} files, {total_bytes / 1024 / 1024:.1f} MB")
    print("Checked: local links, anchors, unique IDs, CNAME, contact form, file limits, and private exclusions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
