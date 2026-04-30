#!/usr/bin/env python3
"""Direct script entry point for project-level MCP configs."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from deepseek_mcp.server import main


if __name__ == "__main__":
    main()
