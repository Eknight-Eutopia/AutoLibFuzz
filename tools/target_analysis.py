from __future__ import annotations

import os
import re
from pathlib import Path


HEADER_SUFFIXES = {".h", ".hh", ".hpp", ".hxx"}
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx"}
INTERESTING_API_KEYWORDS = (
    "parse",
    "decode",
    "encode",
    "read",
    "load",
    "from_",
    "open",
    "deserialize",
    "inflate",
    "decompress",
    "message",
    "config",
    "url",
    "uri",
    "json",
    "xml",
    "http",
    "mail",
    "refspec",
    "pack",
    "object",
    "token",
    "escape",
    "verify",
    "tracker",
    "torrent",
    "bdecode",
    "utf8",
    "buffer",
)
BORING_API_KEYWORDS = (
    "free",
    "dispose",
    "shutdown",
    "version",
    "init",
    "cleanup",
    "options",
    "owner",
)
INTERESTING_PARAM_TOKENS = (
    "const char *",
    "char const *",
    "const void *",
    "void *",
    "const uint8_t *",
    "uint8_t *",
    "const unsigned char *",
    "unsigned char *",
    "size_t",
    "string_view",
    "std::string",
    "buffer",
    "buf",
    "data",
    "len",
)
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "vendor",
    "third_party",
    "third-party",
    "deps",
    "dist",
    "out",
    "target",
}
SKIP_DIR_PREFIXES = ("build", "cmake-build")
DOC_CANDIDATES = (
    "README.md",
    "README.rst",
    "README.txt",
    "FUZZING.md",
    "FUZZING.rst",
    "fuzzers/README.md",
    "fuzzers/README.rst",
)
BUILD_FILES = (
    "CMakeLists.txt",
    "Makefile",
    "GNUmakefile",
    "Jamfile",
    "meson.build",
    "configure.ac",
    "configure.in",
)
HEADER_ROOT_NAMES = ("include", "inc", "public", "headers")
STATIC_LIBRARY_NAMES = (".a", ".lib")
MAX_HEADER_SCAN = 40


def _relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _should_skip_dir(dirname: str) -> bool:
    if dirname in SKIP_DIR_NAMES:
        return True
    return dirname.startswith(SKIP_DIR_PREFIXES)


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [dirname for dirname in dirnames if not _should_skip_dir(dirname)]
        current_path = Path(current_root)
        for filename in filenames:
            files.append(current_path / filename)
    return files


def _find_top_level_dirs(root: Path) -> list[str]:
    dirs: list[str] = []
    for child in sorted(root.iterdir(), key=lambda path: path.name):
        if child.is_dir() and not _should_skip_dir(child.name) and not child.name.startswith("."):
            dirs.append(child.name)
    return dirs


def _find_docs(root: Path) -> list[str]:
    docs: list[str] = []
    for rel in DOC_CANDIDATES:
        path = root / rel
        if path.is_file():
            docs.append(rel)
    return docs


def _find_build_files(root: Path) -> list[str]:
    build_files: list[str] = []
    for rel in BUILD_FILES:
        path = root / rel
        if path.is_file():
            build_files.append(rel)
    fuzzers_cmake = root / "fuzzers" / "CMakeLists.txt"
    if fuzzers_cmake.is_file():
        build_files.append("fuzzers/CMakeLists.txt")
    return build_files


def _find_static_libraries(root: Path, limit: int = 8) -> list[str]:
    libraries: list[str] = []
    for current_root, _, filenames in os.walk(root):
        current_path = Path(current_root)
        for filename in filenames:
            path = current_path / filename
            if path.suffix in STATIC_LIBRARY_NAMES:
                libraries.append(_relpath(path, root))
            if len(libraries) >= limit:
                break
        if len(libraries) >= limit:
            break
    return libraries


def _find_existing_fuzzers(root: Path, limit: int = 20) -> list[str]:
    fuzzers: list[str] = []
    for path in _iter_files(root):
        rel = _relpath(path, root)
        rel_lower = rel.lower()
        if "fuzz" not in rel_lower:
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES | HEADER_SUFFIXES:
            continue
        fuzzers.append(rel)
        if len(fuzzers) >= limit:
            break
    return sorted(fuzzers)


def _header_path_score(path: Path, root: Path) -> int:
    rel = _relpath(path, root).lower()
    score = 0
    if rel.startswith("include/"):
        score += 5
    if "/internal/" in rel or "/detail/" in rel or "/private/" in rel:
        score -= 5
    for keyword in INTERESTING_API_KEYWORDS:
        if keyword in rel:
            score += 2
    if rel.count("/") <= 2:
        score += 2
    return score


def _find_public_headers(root: Path, limit: int = 20) -> list[Path]:
    headers: list[Path] = []
    for root_name in HEADER_ROOT_NAMES:
        header_root = root / root_name
        if not header_root.is_dir():
            continue
        for path in _iter_files(header_root):
            if path.suffix.lower() in HEADER_SUFFIXES:
                headers.append(path)

    if not headers:
        for path in _iter_files(root):
            if path.suffix.lower() in HEADER_SUFFIXES and "test" not in _relpath(path, root).lower():
                headers.append(path)

    headers.sort(key=lambda path: (-_header_path_score(path, root), _relpath(path, root)))
    return headers[:limit]


def _iter_function_prototypes(path: Path) -> list[tuple[int, str, str, str]]:
    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    raw_text = re.sub(r"/\*.*?\*/", "", raw_text, flags=re.S)
    raw_text = re.sub(r"//.*", "", raw_text)
    raw_lines = raw_text.splitlines()

    prototypes: list[tuple[int, str, str, str]] = []
    statement_lines: list[str] = []
    statement_start = 0

    for line_no, raw_line in enumerate(raw_lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            if not statement_lines:
                continue
        if stripped.startswith("#") or stripped.startswith("//"):
            if not statement_lines:
                continue
        if not statement_lines:
            statement_start = line_no
        statement_lines.append(stripped)

        if ";" not in stripped:
            continue

        statement = " ".join(line for line in statement_lines if line)
        statement_lines = []
        statement = re.sub(r"\s+", " ", statement)
        if not statement.endswith(";"):
            continue
        if "(" not in statement or ")" not in statement:
            continue
        if "typedef" in statement or statement.startswith("struct ") or statement.startswith("enum "):
            continue
        if "{" in statement or "}" in statement:
            continue
        if len(statement) > 320:
            continue
        if "friend " in statement or "private:" in statement or "protected:" in statement:
            continue

        match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*;$", statement)
        if not match:
            continue

        function_name = match.group(1)
        params = match.group(2)
        if function_name in {"if", "for", "while", "switch", "return", "sizeof"}:
            continue

        prototypes.append((statement_start, function_name, params, statement))

    return prototypes


def _candidate_score(path: Path, root: Path, function_name: str, params: str, signature: str) -> int:
    score = _header_path_score(path, root)
    rel_lower = _relpath(path, root).lower()
    name_lower = function_name.lower()
    params_lower = params.lower()
    signature_lower = signature.lower()

    for keyword in INTERESTING_API_KEYWORDS:
        if keyword in name_lower:
            score += 4
    for keyword in BORING_API_KEYWORDS:
        if keyword in name_lower:
            score -= 5
    for token in INTERESTING_PARAM_TOKENS:
        if token in params_lower:
            score += 2
    if signature.count(",") <= 4:
        score += 1
    if "deprecated" in signature_lower:
        score -= 10
    if "deprecated" in rel_lower:
        score -= 8
    if "callback" in signature_lower or "_cb" in name_lower or "git_callback" in signature_lower:
        score -= 8
    if re.search(r"\b[A-Za-z0-9_]+_cb\b", signature_lower):
        score -= 8
    if "friend " in signature_lower or "private:" in signature_lower:
        score -= 10
    return score


def _find_api_candidates(root: Path, limit: int = 12) -> list[str]:
    candidates: list[tuple[int, str, int, str]] = []
    for header in _find_public_headers(root, limit=MAX_HEADER_SCAN):
        rel = _relpath(header, root)
        for line_no, function_name, params, signature in _iter_function_prototypes(header):
            score = _candidate_score(header, root, function_name, params, signature)
            if score <= 0:
                continue
            candidates.append((score, rel, line_no, signature))

    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

    unique_signatures: list[str] = []
    seen_signatures: set[str] = set()
    for _, rel, line_no, signature in candidates:
        normalized = signature.lower()
        if normalized in seen_signatures:
            continue
        seen_signatures.add(normalized)
        unique_signatures.append(f"{rel}:{line_no} | {signature}")
        if len(unique_signatures) >= limit:
            break
    return unique_signatures


def build_harness_context(target_library_path: str) -> str:
    root = Path(target_library_path).expanduser().resolve()
    if not root.is_dir():
        return f"TargetHarnessContext\nerror: `{root}` is not a directory."

    top_level_dirs = _find_top_level_dirs(root)
    docs = _find_docs(root)
    build_files = _find_build_files(root)
    static_libraries = _find_static_libraries(root)
    existing_fuzzers = _find_existing_fuzzers(root)
    public_headers = [_relpath(path, root) for path in _find_public_headers(root)]
    api_candidates = _find_api_candidates(root)

    lines = [
        "TargetHarnessContext",
        f"root: {root}",
        "strategy: prefer existing fuzzers and public headers; avoid scanning tests, deps, and build outputs.",
        f"top_level_dirs: {', '.join(top_level_dirs[:10]) or '(none)'}",
    ]

    if docs:
        lines.append(f"docs: {', '.join(docs[:6])}")
    if build_files:
        lines.append(f"build_files: {', '.join(build_files[:6])}")
    if static_libraries:
        lines.append(f"static_libraries: {', '.join(static_libraries[:6])}")

    if existing_fuzzers:
        lines.append("existing_fuzzers:")
        lines.extend(f"- {path}" for path in existing_fuzzers[:12])

    if public_headers:
        lines.append("public_headers_to_check_first:")
        lines.extend(f"- {path}" for path in public_headers[:10])

    if api_candidates:
        lines.append("candidate_apis:")
        lines.extend(f"- {candidate}" for candidate in api_candidates)

    return "\n".join(lines)
