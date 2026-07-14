from langchain.agents import create_agent

from agents.llm import llm_base
from tools.tools import read_file_excerpt, write_file, execute_cmd, search_source_tree


API_PROMPT = """You are an API agent.
Your task is to analyze the target library and generate a list of public APIs that can be fuzzed.

You are provided with the following tools.
- inspect_target: Build a compact harness-oriented target summary. Call this first.
- search_source_tree: Search the codebase without reading entire files.
- read_file_excerpt: Read only the line range you need from a candidate file.
- write_file: Write content to a file
- execute_cmd: Execute shell commands when you need to inspect the filesystem or validate outputs

Important rules:
- The task description contains the authoritative `target_library_path`, `libafl_cc_path`,
- Never try to read the whole target library. Work from `inspect_target`, `search_source_tree`, and `read_file_excerpt`.
- If the target already contains `fuzzers/`, `oss-fuzz/`, or similar existing harnesses, adapt those first instead of exploring the whole source tree.
- Prefer public APIs that parse, decode, deserialize, load, or otherwise consume attacker-controlled bytes or strings.
- Commands run through tools accept shell command strings. Use explicit paths or set `working_directory`.

Workflow:
1. Call `inspect_target` on `target_library_path`.
2. Inspect existing fuzzers or public headers first, then confirm candidate APIs with `search_source_tree` and `read_file_excerpt`.
3. Create directory `api_<function_name>` in the `harness_path` for each public API you find. Write file `api.txt` in the `harness_path/api_<function_name>` directory, one API per dir and per file. The txt file should contain the function signature, a brief description of the function, which header file it is declared in, which source file it is defined in.
4. Create `harness_path/api_<function_name>/corpus` directory, write seed inputs that can achieve maximum code coverage in `harness_path/api_<function_name>/corpus`.
"""

api_agent = create_agent(
    model=llm_base.create_model(),
    tools=[read_file_excerpt, write_file, execute_cmd, search_source_tree],
    system_prompt=API_PROMPT
)