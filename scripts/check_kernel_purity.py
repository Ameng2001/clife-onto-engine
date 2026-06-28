#!/usr/bin/env python3
"""内核防腐 CI —— 红线的自动化执法。

扫描 clife_onto_engine/ 源码，若出现任何行业词汇即失败。
内核必须与行业无关；行业概念只能存在于 plugins/ 与 tenants/。

用法:  python scripts/check_kernel_purity.py   （退出码非 0 即违规）
"""
from __future__ import annotations

import pathlib
import sys

KERNEL = pathlib.Path(__file__).resolve().parent.parent / "clife_onto_engine"

# 行业词汇黑名单（可扩充）。命中即说明"草"漏进了内核。
FORBIDDEN = [
    "草", "种质", "碳汇", "载畜", "乡土", "苜蓿", "盖度", "退化",
    "牧", "饲", "遥感", "grass", "germplasm", "carbon", "forage",
]


def main() -> int:
    violations: list[str] = []
    for path in KERNEL.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for word in FORBIDDEN:
                if word in line:
                    violations.append(f"{path.relative_to(KERNEL.parent)}:{lineno}: 行业词汇 '{word}' → {line.strip()}")
    if violations:
        print("内核防腐检查失败 —— 行业概念漏进了内核：", file=sys.stderr)
        for v in violations:
            print("  " + v, file=sys.stderr)
        return 1
    print("内核防腐检查通过：clife_onto_engine/ 无行业词汇。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
