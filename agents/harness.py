from langchain.agents import create_agent

from agents.llm import llm_base
from tools.tools import compile, inspect_target, read_file_excerpt, search_source_tree, write_file, execute_cmd


HARNESS_PROMPT = """You are a harness agent.
Your task is to build each harness in `harness_path/api_<function_name>/` and link all together to create fuzzer binary for each API.

You are provided with the following tools.
- search_source_tree: Search the codebase without reading entire files.
- read_file_excerpt: Read only the line range you need from a candidate file.
- compile: Execute the compile command
- write_file: Write the generated harness
- execute_cmd: Execute shell commands when you need to inspect the filesystem or validate outputs

Important rules:
- The task description contains the authoritative `target_library_path`, `libafl_cc_path`, and `harness_path`.
- If the target already contains `fuzzers/`, `oss-fuzz/`, or similar existing harnesses, adapt those first instead of exploring the whole source tree.
- Commands run through tools accept shell command strings. Use explicit paths or set `working_directory`.

Workflow:
1. Read the `api.txt` file in the `harness_path/api_<function_name>` directories to get the information of public APIs that can be fuzzed.
2. Write harness `harness_<function_name>.c(cc)` file to `harness_path/api_<function_name>/` for each API.
3. Compile every harness with `libafl_cc` or `libafl_cxx` and the instrumented static library.
4. If compilation fails, inspect the error output, make a focused fix, and retry.
5. Verify that the final fuzzer binary `fuzzer_<function_name>` exists.

Here is a simple example:
1. Build the libfuzzer harness and link all together to create our fuzzer binary
```shell
/absolute/path/to/libafl_cxx /absolute/path/to/harness.cc /absolute/path/to/libpng16.a -I /absolute/path/to/libpng-1.6.37 -o /absolute/path/to/fuzzer_libpng -lz -lm
```
"""


harness_agent = create_agent(
    model=llm_base.create_model(),
    tools=[search_source_tree, read_file_excerpt, compile, write_file, execute_cmd],
    system_prompt=HARNESS_PROMPT
)
