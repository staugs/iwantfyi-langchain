"""Minimal LangChain agent that uses iwant.fyi as a tool source.

This example uses langgraph's prebuilt react agent. Replace ChatOpenAI with
any LangChain-compatible chat model. Set IWANT_API_KEY in your environment.

Install:
    pip install iwantfyi-langchain langchain-openai langgraph

Run:
    IWANT_API_KEY=iwant_ak_... OPENAI_API_KEY=sk-... python examples/basic_agent.py
"""

import os
import sys

from iwantfyi_langchain import get_iwant_tools

try:
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent
except ImportError:
    print(
        "This example requires langchain-openai and langgraph. Install with:\n"
        "  pip install langchain-openai langgraph",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    api_key = os.environ.get("IWANT_API_KEY")
    if not api_key:
        print("IWANT_API_KEY not set. Get one at https://iwant.fyi.", file=sys.stderr)
        sys.exit(1)

    tools = get_iwant_tools(api_key=api_key)
    print(f"Loaded {len(tools)} iwant.fyi tools: {[t.name for t in tools]}\n")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_react_agent(llm, tools)

    prompt = (
        "I need a 1/4-inch drive torque wrench rated 25-100 ft-lb, good condition or better, "
        "under $150, available in Brooklyn. Create a Want on iwant.fyi and show me the matches."
    )
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    final = result["messages"][-1].content
    print(final)


if __name__ == "__main__":
    main()
