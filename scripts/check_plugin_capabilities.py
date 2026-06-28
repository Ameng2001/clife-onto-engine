#!/usr/bin/env python3
"""插件静态能力 CI —— 进程内沙箱的兜底执法。

Capability 在运行时收窄了能力面，但纯进程内无法物理阻止 `import socket` 之类逃逸。
本检查静态扫描 plugins/ 运行代码，拦截两类越界：
  1. 逃逸：网络 / 子进程 / 动态执行（socket/requests/subprocess/eval/exec/__import__…）
  2. 内核内部直达：绕过 Capability 去摸 _base / _view / changeset / 名称改写私有等。

副作用必须经 cap.emit_effect 声明、由内核编排；读写必须经 Capability。
（demo/test 文件不在运行面，跳过。）

用法:  python scripts/check_plugin_capabilities.py
"""
from __future__ import annotations

import pathlib
import re
import sys

PLUGINS = pathlib.Path(__file__).resolve().parent.parent / "plugins"

FORBIDDEN = [
    (r"\bimport\s+(socket|urllib|requests|http|httplib|smtplib|ftplib|telnetlib)\b", "网络访问"),
    (r"\bfrom\s+(socket|urllib|requests|http|smtplib|ftplib)\b", "网络访问"),
    (r"\bimport\s+subprocess\b|\bsubprocess\.", "子进程"),
    (r"\bos\.(system|popen|exec|spawn)", "shell 逃逸"),
    (r"\beval\(|\bexec\(|\b__import__\(", "动态执行"),
    (r"_Capability__|\._base\b|\._view\b|\.changeset\b|\._stage\(|_set_confidence|_add_effect|_add_evidence", "绕过 Capability 直达内核内部"),
]


def main() -> int:
    violations: list[str] = []
    for path in PLUGINS.rglob("*.py"):
        if "demo" in path.name or path.name.startswith("test_"):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pat, why in FORBIDDEN:
                if re.search(pat, line):
                    violations.append(f"{path.relative_to(PLUGINS.parent)}:{lineno}: [{why}] {line.strip()}")
    if violations:
        print("插件能力检查失败 —— 越界访问：", file=sys.stderr)
        for v in violations:
            print("  " + v, file=sys.stderr)
        return 1
    print("插件能力检查通过：plugins/ 无网络/子进程/动态执行/内核内部直达。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
