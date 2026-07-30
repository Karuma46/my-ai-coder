import json
import re
from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse


def slugify(value: str, *, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def repository_slug(path: str, name: str) -> str:
    parsed = urlparse(path)
    candidate_path = parsed.path if parsed.scheme and parsed.netloc else path
    candidate = PurePosixPath(candidate_path.rstrip("/")).name.removesuffix(".git")
    return candidate or slugify(name, fallback="project")


def extract_github_value(value: Any, keys: Iterable[str]) -> Any:
    wanted = set(keys)
    return _search_github_value(value, wanted)


def extract_github_number(
    value: Any,
    keys: Iterable[str],
    *,
    url_segment: str,
) -> int | None:
    candidate = extract_github_value(value, keys)
    if isinstance(candidate, int) and not isinstance(candidate, bool):
        return candidate
    if isinstance(candidate, str) and candidate.isdigit():
        return int(candidate)

    url = extract_github_value(
        value,
        ("url", "html_url", "issue_url", "pull_request_url"),
    )
    if not isinstance(url, str):
        return None
    match = re.search(rf"/{re.escape(url_segment)}/(\d+)(?:[/?#]|$)", url)
    return int(match.group(1)) if match else None


def _search_github_value(value: Any, keys: set[str]) -> Any:
    if hasattr(value, "model_dump"):
        return _search_github_value(value.model_dump(mode="json"), keys)

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                return _search_github_value(json.loads(stripped), keys)
            except json.JSONDecodeError:
                return None
        return None

    if isinstance(value, Mapping):
        for key in keys:
            candidate = value.get(key)
            if candidate is not None:
                return candidate
        for candidate in value.values():
            found = _search_github_value(candidate, keys)
            if found is not None:
                return found
        return None

    if isinstance(value, (list, tuple)):
        for candidate in value:
            found = _search_github_value(candidate, keys)
            if found is not None:
                return found
    return None
