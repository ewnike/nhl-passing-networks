#!/usr/bin/env python
"""Regenerate docs/data_contract.md from src/possnet/schema/contract.py."""

from __future__ import annotations

from possnet.paths import repo_path
from possnet.schema.render import render_contract_markdown


def main() -> None:
    out = repo_path("docs/data_contract.md")
    out.write_text(render_contract_markdown(), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
