# -*- coding: utf-8 -*-
"""md2pdf 命令行入口。"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .core import build, BuildError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="md2pdf",
        description="给一个主 Markdown 文件,自动顺着链接收集全部关联 .md 并生成单个 PDF。",
    )
    parser.add_argument("main", help="主 Markdown 文件(如 index.md)")
    parser.add_argument("-o", "--output", help="输出 PDF 路径(默认:主文件同目录、同名 .pdf)")
    parser.add_argument("--title", help="文档标题(默认取主文件的第一个一级标题)")
    parser.add_argument("--css", help="自定义 CSS 样式表(默认用内置样式)")
    parser.add_argument("--no-toc", action="store_true", help="不生成目录")
    parser.add_argument("-q", "--quiet", action="store_true", help="安静模式,少打印")
    parser.add_argument("-V", "--version", action="version",
                        version=f"md2pdf {__version__}")
    args = parser.parse_args(argv)

    try:
        out = build(
            args.main,
            output=args.output,
            toc=not args.no_toc,
            css=args.css,
            title=args.title,
            verbose=not args.quiet,
        )
    except BuildError as e:
        print("错误:" + str(e), file=sys.stderr)
        return 1
    print(f"✓ 已生成:{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
