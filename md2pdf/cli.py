# -*- coding: utf-8 -*-
"""md2pdf 命令行入口。

两种用法:
  1) 直接给路径:            md2pdf index.md [选项]
     (在终端里输入 `md2pdf ` 后把文件拖进来也属于这种——shell 会自动补全路径)
  2) 交互模式(不带参数):   md2pdf
     运行后把主 .md 拖进终端、回车即可;会自动清理拖拽产生的转义空格与引号。
"""
from __future__ import annotations

import argparse
import os
import shlex
import sys

from . import __version__
from .core import build, BuildError


def clean_dragged_path(raw: str) -> str:
    """清理「把文件拖进终端」得到的路径。

    终端拖拽常见形态:
      /Users/me/my\\ file.md        (空格被反斜杠转义)
      '/Users/me/my file.md'        (单引号包裹,iTerm)
      "/Users/me/my file.md"        (双引号包裹)
      末尾还常带一个空格
    用 shlex 解析可一次性处理转义与引号(Windows 下保留反斜杠分隔符)。
    """
    raw = raw.strip()
    if not raw:
        return raw
    try:
        parts = shlex.split(raw, posix=(os.name != "nt"))
        if len(parts) == 1:
            return parts[0]
        if parts:
            # 多个 token:通常是未转义的空格路径,拼回去再去引号
            return raw.strip().strip("'\"")
    except ValueError:
        pass
    return raw.strip().strip("'\"")


def _prompt(text: str) -> str:
    try:
        return input(text)
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def interactive() -> int:
    print("md2pdf —— 把主 Markdown 文件拖进终端,回车即可生成 PDF。\n")
    raw = _prompt("① 主 .md 文件(拖进来 / 粘贴路径,回车):").strip()
    main_file = clean_dragged_path(raw)
    if not main_file:
        print("未提供文件,已取消。", file=sys.stderr)
        return 1
    if not os.path.isfile(main_file):
        print(f"错误:文件不存在 -> {main_file}", file=sys.stderr)
        return 1
    if not main_file.lower().endswith(".md"):
        print(f"提示:这不是 .md 文件({main_file}),仍尝试处理…", file=sys.stderr)

    out_raw = _prompt("② 输出 PDF 路径(直接回车=源目录同名 .pdf):").strip()
    output = clean_dragged_path(out_raw) if out_raw else None

    print()
    return _run(main_file, output, toc=True, verbose=True)


def _run(main_file, output, toc, verbose, css=None, title=None) -> int:
    try:
        out = build(main_file, output=output, toc=toc, css=css,
                    title=title, verbose=verbose)
    except BuildError as e:
        print("错误:" + str(e), file=sys.stderr)
        return 1
    print(f"✓ 已生成:{out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="md2pdf",
        description="给一个主 Markdown 文件,自动顺着链接收集全部关联 .md 并生成单个 PDF。"
                    "不带参数运行则进入交互模式(把文件拖进终端即可)。",
    )
    parser.add_argument("main", nargs="?",
                        help="主 Markdown 文件(如 index.md);省略则进入交互模式")
    parser.add_argument("-o", "--output", help="输出 PDF 路径(默认:主文件同目录、同名 .pdf)")
    parser.add_argument("--title", help="文档标题(默认取主文件的第一个一级标题)")
    parser.add_argument("--css", help="自定义 CSS 样式表(默认用内置样式)")
    parser.add_argument("--no-toc", action="store_true", help="不生成目录")
    parser.add_argument("-q", "--quiet", action="store_true", help="安静模式,少打印")
    parser.add_argument("-V", "--version", action="version",
                        version=f"md2pdf {__version__}")
    args = parser.parse_args(argv)

    if not args.main:
        return interactive()

    return _run(args.main, args.output, toc=not args.no_toc,
                verbose=not args.quiet, css=args.css, title=args.title)


if __name__ == "__main__":
    raise SystemExit(main())
