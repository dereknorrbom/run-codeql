"""SARIF parsing and summary rendering."""

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path

_DB_MIRROR_RE = re.compile(r"(?:^|/)\.codeql/db-[^/]+/src/(?P<src>.+)$")


@dataclass(frozen=True)
class SarifSummary:
    """Rendered SARIF summary and metadata needed for exit semantics."""

    text: str
    total_findings: int
    read_error: bool
    matched_findings: int = 0  # findings that passed --files filter (before limit/offset)


def _uri_matches(uri: str, patterns: list[str]) -> bool:
    """Return True if *uri* matches any of the fnmatch *patterns*.

    Each pattern is tested against both the full URI and the basename so
    callers can pass either ``src/foo.py`` or just ``foo.py``.
    """
    for pat in patterns:
        if fnmatch.fnmatch(uri, pat):
            return True
        if fnmatch.fnmatch(uri, f"*/{pat}"):
            return True
    return False


def _normalize_uri(uri: str) -> str:
    """Normalize SARIF artifact URIs to stable, source-like paths.

    CodeQL may emit artifact URIs that point into the generated database mirror,
    e.g. ``.codeql/db-python/src/<abs-repo-path>/src/file.py``. This function
    maps those back to repository-relative paths when possible so findings are
    not shown twice (real path + mirror path).
    """
    if not uri:
        return ""

    normalized = uri.replace("\\", "/")
    if normalized.startswith("file://"):
        normalized = normalized[7:]

    match = _DB_MIRROR_RE.search(normalized)
    if match:
        normalized = match.group("src")

    cwd_posix = str(Path.cwd().resolve()).replace("\\", "/")
    cwd_no_leading = cwd_posix.lstrip("/")
    if (
        cwd_posix.startswith("/")
        and not normalized.startswith("/")
        and (normalized == cwd_no_leading or normalized.startswith(cwd_no_leading + "/"))
    ):
        normalized = "/" + normalized

    if normalized.startswith(cwd_posix + "/"):
        normalized = normalized[len(cwd_posix) + 1 :]
    elif normalized == cwd_posix:
        normalized = "."

    return normalized


def build_sarif_summary(
    sarif: Path,
    verbose: bool = False,
    files: list[str] | None = None,
    rules: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> SarifSummary:
    """Build a rendered SARIF summary and metadata for control flow.

    Args:
        sarif:   Path to the ``.sarif`` file.
        verbose: Include per-finding details in the output text.
        files:   Optional list of fnmatch patterns matched against artifact URIs.
        rules:   Optional list of fnmatch patterns matched against rule IDs
                 (e.g. ``['py/unused-import']`` or ``['py/*']``).
        limit:   If set, return at most this many findings (after *offset*).
        offset:  Skip this many findings before applying *limit* (pagination).
    """
    try:
        data = json.loads(sarif.read_text(encoding="utf-8"))
    except Exception as exc:
        return SarifSummary(
            text=f"  (could not read SARIF: {exc})", total_findings=0, read_error=True
        )

    # Collect all matching results first so we can apply offset/limit uniformly.
    matched: list[dict] = []
    rules_map: dict[str, dict] = {}
    seen_keys: set[tuple[str, str, int | str, str, str]] = set()

    for run in data.get("runs", []):
        rules_map.update(
            {r["id"]: r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
        )
        for result in run.get("results", []):
            loc = result.get("locations", [{}])[0]
            phys = loc.get("physicalLocation", {})
            raw_uri = phys.get("artifactLocation", {}).get("uri", "")
            uri = _normalize_uri(raw_uri)
            line = phys.get("region", {}).get("startLine", "")
            rule_id = result.get("ruleId", "")
            level = result.get("level", "warning")
            message = re.sub(
                r"\[([^\]]+)\]\(\d+\)", r"\1", result.get("message", {}).get("text", "")
            )

            if files is not None:
                if not _uri_matches(uri, files):
                    continue
            if rules is not None:
                if not any(fnmatch.fnmatch(rule_id, pat) for pat in rules):
                    continue

            dedupe_key = (rule_id, level, line, uri, message)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            matched.append(result)

    # Apply pagination.
    paginated = matched[offset:]
    if limit is not None:
        paginated = paginated[:limit]

    counts: dict[str, int] = {}
    finding_lines: list[str] = []

    for result in paginated:
        level = result.get("level", "warning")
        counts[level] = counts.get(level, 0) + 1

        if verbose:
            rule_id = result.get("ruleId", "unknown")
            rule = rules_map.get(rule_id, {})
            short_desc = rule.get("shortDescription", {}).get("text", "")
            message = result.get("message", {}).get("text", "")
            message = re.sub(r"\[([^\]]+)\]\(\d+\)", r"\1", message)
            loc = result.get("locations", [{}])[0]
            phys = loc.get("physicalLocation", {})
            uri = _normalize_uri(phys.get("artifactLocation", {}).get("uri", ""))
            line = phys.get("region", {}).get("startLine", "")
            location = f"{uri}:{line}" if line else uri
            finding_lines.append(
                f"  [{level}] {rule_id}\n"
                f"    {short_desc}\n"
                f"    {location}\n"
                f"    {message}"
            )

    total_matched = len(matched)
    total_shown = len(paginated)
    total = sum(counts.values())

    count_lines = [f"  {level}: {counts[level]}" for level in sorted(counts)]
    if files is not None or rules is not None or limit is not None or offset:
        count_lines.append(f"  Shown: {total_shown}  (matched: {total_matched})")
    else:
        count_lines.append(f"  Total: {total}")

    if verbose and finding_lines:
        return SarifSummary(
            text="\n".join(count_lines) + "\n\n" + "\n\n".join(finding_lines),
            total_findings=total,
            read_error=False,
            matched_findings=total_matched,
        )
    return SarifSummary(
        text="\n".join(count_lines),
        total_findings=total,
        read_error=False,
        matched_findings=total_matched,
    )


def summarize_sarif(sarif: Path, lang: str, verbose: bool = False) -> str:
    """Render a SARIF summary string for CLI output."""
    del lang  # reserved for future language-specific formatting
    return build_sarif_summary(sarif, verbose=verbose).text
