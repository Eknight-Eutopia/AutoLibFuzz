import shutil
import subprocess
from pathlib import Path

from langchain.tools import tool

from tools.target_analysis import build_harness_context

@tool
def compile(
    compile_command: str,
    working_directory: str = "",
) -> str:
    """Compile code with an explicit command string. Prefer absolute paths or set working_directory."""

    try:
        result = subprocess.run(
            compile_command,
            capture_output=True,
            text=True,
            shell=True,
            cwd=working_directory or None,
        )
        if result.returncode != 0:
            return f"Compilation failed with error:\n{result.stderr}"
        else:
            return f"Compilation succeeded:\n{result.stdout}"
    except Exception as e:
        return f"An error occurred while running the compile command: {str(e)}"
    


@tool
def read_file(
    file_path: str,
) -> str:
    """Read the content of a file"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read()
        return content
    except Exception as e:
        return f"An error occurred while reading the file: {str(e)}"

@tool
def write_file(
    file_path: str,
    content: str,
) -> str:
    """Write content to a file"""
    try:
        with open(file_path, "w") as file:
            file.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"An error occurred while writing to the file: {str(e)}"

@tool
def inspect_target(
    target_library_path: str,
) -> str:
    """Build a compact harness-oriented summary of the target library. Call this before searching or reading snippets."""
    return build_harness_context(target_library_path)

@tool
def search_source_tree(
    target_library_path: str,
    query: str,
    max_results: int = 30,
) -> str:
    """Search filtered source, header, doc, and build files in the target library. Use this before reading file excerpts."""
    search_root = Path(target_library_path).expanduser().resolve()
    if not search_root.is_dir():
        return f"Search failed: `{search_root}` is not a directory."

    max_results = max(1, min(max_results, 100))
    rg_path = shutil.which("rg")

    try:
        if rg_path:
            command = [
                rg_path,
                "--line-number",
                "--no-heading",
                "--color",
                "never",
                "--hidden",
                "-g",
                "*.c",
                "-g",
                "*.cc",
                "-g",
                "*.cpp",
                "-g",
                "*.cxx",
                "-g",
                "*.h",
                "-g",
                "*.hh",
                "-g",
                "*.hpp",
                "-g",
                "*.hxx",
                "-g",
                "*.md",
                "-g",
                "*.rst",
                "-g",
                "*.txt",
                "-g",
                "CMakeLists.txt",
                "-g",
                "Makefile",
                "-g",
                "GNUmakefile",
                "-g",
                "Jamfile",
                "-g",
                "meson.build",
                "-g",
                "configure.ac",
                "-g",
                "configure.in",
                "-g",
                "!**/.git/**",
                "-g",
                "!**/build*/**",
                "-g",
                "!**/cmake-build*/**",
                "-g",
                "!**/deps/**",
                "-g",
                "!**/third_party/**",
                "-g",
                "!**/third-party/**",
                "-g",
                "!**/vendor/**",
                "-g",
                "!**/out/**",
                "-g",
                "!**/test/**",
                "-g",
                "!**/tests/**",
                "-g",
                "!**/simulation/**",
                "-g",
                "!**/benchmarks/**",
                query,
                str(search_root),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
        else:
            result = subprocess.run(
                [
                    "grep",
                    "-RIn",
                    "--exclude-dir=.git",
                    "--exclude-dir=deps",
                    "--exclude-dir=third_party",
                    "--exclude-dir=third-party",
                    "--exclude-dir=vendor",
                    "--exclude-dir=out",
                    query,
                    str(search_root),
                ],
                capture_output=True,
                text=True,
            )
    except Exception as e:
        return f"Search failed with error: {str(e)}"

    if result.returncode not in (0, 1):
        return f"Search failed with error:\n{result.stderr}"

    matches = [line for line in result.stdout.splitlines() if line.strip()]
    if not matches:
        return f"No matches found for `{query}` under `{search_root}`."

    limited_matches = matches[:max_results]
    body = "\n".join(limited_matches)
    if len(matches) > max_results:
        body += f"\n... truncated {len(matches) - max_results} more matches"
    return body

@tool
def read_file_excerpt(
    file_path: str,
    start_line: int = 1,
    max_lines: int = 120,
) -> str:
    """Read only a bounded excerpt from a text file. Prefer this over full-file reads when inspecting candidate code."""
    try:
        path = Path(file_path).expanduser().resolve()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return f"An error occurred while reading the file excerpt: {str(e)}"

    start_line = max(1, start_line)
    max_lines = max(1, min(max_lines, 200))
    end_line = min(len(lines), start_line + max_lines - 1)

    excerpt = [f"{line_no:5d}: {lines[line_no - 1]}" for line_no in range(start_line, end_line + 1)]
    header = f"{path} lines {start_line}-{end_line} of {len(lines)}"
    return f"{header}\n" + "\n".join(excerpt)

@tool
def execute_cmd(
    command: str,
    working_directory: str = "",
) -> str:
    """Execute a shell command string. Prefer explicit absolute paths or set working_directory."""

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            cwd=working_directory or None,
        )
        if result.returncode != 0:
            return f"Command failed with error:\n{result.stderr}"
        else:
            return f"Command succeeded:\n{result.stdout}"
    except Exception as e:
        return f"An error occurred while executing the command: {str(e)}"
