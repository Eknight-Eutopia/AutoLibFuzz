from langchain.agents import create_agent

from agents.llm import llm_base
from tools.tools import compile, read_file, write_file, execute_cmd

INSTRUMENT_PROMPT = """You are a instrument agent.
Your task is to instrument target library with libafl_cc.

You are provided with the following tools.
- compile: Execute the compile command
- read_file: Read the content of a file
- execute_cmd: Execute shell commands when you need to inspect the filesystem or validate outputs

Check if there is `libafl_cc` executable file in state's libafl_cc_path.
Read the README.md file in target library path at state's target_library_path, check if there is any instruction about `how to compile`.
Generate new compile command with `libafl_cc` tool. Make sure this command can successfully run and compile.

Here is a simple example:
1. Compile libpng with libafl_cc compiler wrapper:
```shell
./configure --enable-shared=no --with-pic=yes --enable-hardware-optimizations=yes
make CC="$(pwd)/../target/release/libafl_cc" CXX="$(pwd)/../target/release/libafl_cxx" -j `nproc`
```
This will build static lib at `libpng-1.6.37/.libs/libpng16.a`
"""

instrument_agent = create_agent(
    model=llm_base.create_model(),
    tools=[compile, read_file, execute_cmd],
    system_prompt=INSTRUMENT_PROMPT
)
