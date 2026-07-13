import os
import logging
import argparse

from agents.main_agent import main_agent
from config.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langchain_openai").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--target", help="target library path")
args = parser.parse_args()

def main():
    logger.info("Hello from AutoLibFuzz!")
    res = main_agent.invoke(
        {"messages": [{"role": "user", "content": f"Check target files in `{(os.path.abspath(args.target))}` and try to generate fuzzer with libafl, libafl_cc path: `{config['libafl_cc']['path']}`, harness path: `{config['harness']['path']}`"}]},
    )
    logger.debug(f"Response: {res}")
    logger.info(f"Response: {res['messages'][-1].content}")

if __name__ == "__main__":
    main()
