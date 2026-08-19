# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Launch one of the five yggame demo games.

Examples:
    python examples/run_demos.py list
    python examples/run_demos.py skybound --board
    python examples/run_demos.py signal --commands "talk,choose 0,inspect dock,report"
"""

from yggame_demos.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
