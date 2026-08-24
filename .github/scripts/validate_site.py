#!/usr/bin/env python3
"""Fail closed when the public Sneferu site is incomplete or miswired."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit


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
RESEARCH_SCHEMA = "sneferu.research-pages-deployment/v1"
PUBLIC_HOST = "sneferu.ai"
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
    links: list[dict[str, str | None]] = field(default_factory=list)
    forms: list[dict[str, str | None]] = field(default_factory=list)
    form_fields: list[dict[str, str | None]] = field(default_factory=list)


class Collector(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.document = Document(path=path)
        self._style_depth = 0

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
        if tag == "a":
            self.document.links.append(values)
        if tag in {"input", "textarea", "select"} and values.get("name"):
            self.document.form_fields.append(values)
        if tag == "style":
            self._style_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "style" and self._style_depth:
            self._style_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._style_depth:
            self.document.references.extend(extract_css_urls(data))


def extract_css_urls(text: str) -> list[str]:
    references = []
    for match in CSS_URL.finditer(text):
        reference = match.group(2).strip()
        if reference and not reference.startswith("#"):
            references.append(reference)
    return references


def parse_document(path: Path) -> tuple[Document, str]:
    text = path.read_text(encoding="utf-8")
    parser = Collector(path)
    parser.feed(text)
    parser.close()
    return parser.document, text


def local_target(root: Path, document: Path, reference: str) -> tuple[Path | None, str]:
    reference = reference.strip()
    if not reference or reference == "#":
        return None, ""

    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("//"):
        if parsed.scheme not in {"", "https"} or parsed.hostname != PUBLIC_HOST:
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_manifest_path(value: object) -> PurePosixPath | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path


def validate_research_deployments(root: Path, errors: list[str]) -> dict[str, str]:
    """Verify every frozen research deployment and return its cache token."""

    research_root = root / "research"
    tokens: dict[str, str] = {}
    if not research_root.is_dir():
        return tokens

    manifests = sorted(research_root.glob("*/deployment-manifest.json"))
    if not manifests:
        errors.append("research must contain at least one managed expedition deployment")
        return tokens

    for manifest_path in manifests:
        deployment = manifest_path.parent
        slug = deployment.name
        label = manifest_path.relative_to(root)
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"cannot read research deployment manifest {label}: {exc}")
            continue

        if not isinstance(payload, dict):
            errors.append(f"research deployment manifest must be an object: {label}")
            continue
        if payload.get("schema") != RESEARCH_SCHEMA:
            errors.append(f"unsupported research deployment schema in {label}")
        if payload.get("route") != f"/research/{slug}/":
            errors.append(f"research deployment route does not match its directory: {label}")

        rows = payload.get("runtime_files")
        if not isinstance(rows, list) or not rows:
            errors.append(f"research deployment has no runtime file inventory: {label}")
            continue

        expected: set[PurePosixPath] = set()
        total_bytes = 0
        index_sha = ""
        for row in rows:
            if not isinstance(row, dict):
                errors.append(f"invalid runtime file row in {label}")
                continue
            relative = safe_manifest_path(row.get("path"))
            if relative is None:
                errors.append(f"unsafe runtime file path in {label}: {row.get('path')!r}")
                continue
            if relative in expected:
                errors.append(f"duplicate runtime file in {label}: {relative}")
                continue
            expected.add(relative)

            target = deployment.joinpath(*relative.parts)
            if not target.is_file() or target.is_symlink():
                errors.append(f"missing research runtime file: {target.relative_to(root)}")
                continue

            expected_size = row.get("size")
            actual_size = target.stat().st_size
            if not isinstance(expected_size, int) or expected_size < 0:
                errors.append(f"invalid runtime size in {label}: {relative}")
            elif actual_size != expected_size:
                errors.append(
                    f"research runtime size mismatch: {target.relative_to(root)} "
                    f"(expected {expected_size}, found {actual_size})"
                )
            total_bytes += actual_size

            expected_sha = row.get("sha256")
            if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
                errors.append(f"invalid runtime hash in {label}: {relative}")
                continue
            actual_sha = sha256_file(target)
            if actual_sha != expected_sha:
                errors.append(f"research runtime hash mismatch: {target.relative_to(root)}")
            if relative == PurePosixPath("index.html"):
                index_sha = expected_sha

        actual = {
            PurePosixPath(path.relative_to(deployment).as_posix())
            for path in deployment.rglob("*")
            if path.is_file() and path != manifest_path
        }
        missing = sorted(expected - actual, key=str)
        extra = sorted(actual - expected, key=str)
        for relative in missing:
            errors.append(f"research manifest member is absent: research/{slug}/{relative}")
        for relative in extra:
            errors.append(f"unrecorded research runtime file: research/{slug}/{relative}")

        if payload.get("runtime_bytes") != total_bytes:
            errors.append(f"research runtime byte total mismatch in {label}")
        if not index_sha:
            errors.append(f"research deployment does not inventory index.html: {label}")
        else:
            tokens[slug] = index_sha[:16]

    return tokens


def research_slug(reference: str) -> str | None:
    parsed = urlsplit(reference.strip())
    if (parsed.scheme or parsed.netloc) and parsed.hostname != PUBLIC_HOST:
        return None
    parts = PurePosixPath(unquote(parsed.path).lstrip("/")).parts
    if len(parts) >= 2 and parts[0] == "research":
        return parts[1]
    return None


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

    research_tokens = validate_research_deployments(root, errors)

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
        if any(LOCAL_HOST.search(reference) for reference in document.references):
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
            slug = research_slug(reference)
            if slug in research_tokens:
                versions = parse_qs(urlsplit(reference).query).get("v", [])
                if versions != [research_tokens[slug]]:
                    errors.append(
                        f"research reference in {path.relative_to(root)} must use "
                        f"?v={research_tokens[slug]}: {reference}"
                    )
            if not target.exists() or not target.is_file():
                errors.append(f"broken local reference in {path.relative_to(root)}: {reference}")
                continue
            is_application_state = slug in research_tokens and fragment.startswith("static-view=")
            if fragment and not is_application_state and target.suffix.lower() in {".html", ".htm"}:
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
        contact_links = [attrs for attrs in index.links if "data-contact-link" in attrs]
        if not contact_links:
            errors.append("index.html must contain an in-page contact link")
        elif any(attrs.get("href") != "#contact" for attrs in contact_links):
            errors.append("every contact link must point to #contact")
        if len(index.forms) != 1:
            errors.append(f"index.html must contain one contact form; found {len(index.forms)}")
        else:
            form = index.forms[0]
            if form.get("action") != FORM_ACTION:
                errors.append("contact form action is not the approved Formspree endpoint")
            if (form.get("method") or "").lower() != "post":
                errors.append("contact form method must be POST")
            if form.get("id") != "contact-form" or "data-onsite-submit" not in form:
                errors.append("contact form must use the on-site submission flow")
        if "contact-form-status" not in index.ids:
            errors.append("contact form must include an on-site status message")
        fields = {attrs.get("name"): attrs for attrs in index.form_fields}
        for name, label in (("email", "email address"), ("name", "name"), ("comments", "comments")):
            if name not in fields or "required" not in fields[name]:
                errors.append(f"contact form must require {label}")
        if "company_or_fund" not in fields:
            errors.append("contact form must include company or fund")
        elif "required" in fields["company_or_fund"]:
            errors.append("company or fund must remain optional")

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
    print(
        "Checked: local links, anchors, unique IDs, CNAME, contact form, file limits, "
        "private exclusions, and frozen research deployment receipts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
