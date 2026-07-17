# -*- coding: utf-8 -*-
"""md2pdf 核心逻辑:从一个主 Markdown 文件出发,自动顺着链接收集全部关联的
本地 .md 文件,合并后用 pandoc + Chrome 渲染成单个 PDF。

设计要点
--------
* 只需提供「主文件」(如 index.md)。程序按链接出现顺序做广度优先遍历,收集所有
  可达的本地 .md 文件,天然得到「目录 → 各章」的阅读顺序。
* 跨文件的 .md 链接会被改写成 PDF 内部锚点,合并成单文件后仍可跳转。
* 用 Chrome 无头模式打印 PDF —— 对中文/CJK、分页、@page 页码支持稳定
  (weasyprint 在 macOS 下会丢字,故不采用)。
* pandoc 关闭 yaml_metadata_block / simple_tables / multiline_tables 扩展:
  正文里「一行 --- 紧跟一行文字」的写法会被误判为简单表格,吞掉标题与正文;
  真实表格使用 | 竖线的 pipe_table,不受影响。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSS = os.path.join(HERE, "style.css")

# 收集本地 .md 链接:匹配 ](target) 或 ](target#frag),target 不含空格/#
_LINK_RE = re.compile(r"\]\(\s*([^)\s#]+?)\s*(#[^)]*)?\)")
_H1_RE = re.compile(r"^\s{0,3}#\s+(.+?)\s*#*\s*$", re.M)

PANDOC_FROM = "markdown+raw_html-yaml_metadata_block-simple_tables-multiline_tables"


class BuildError(Exception):
    """构建过程中的可读错误。"""


# --------------------------------------------------------------------------- #
# 外部工具探测
# --------------------------------------------------------------------------- #
def find_pandoc() -> str:
    path = shutil.which("pandoc")
    if not path:
        raise BuildError(
            "未找到 pandoc。请先安装:\n"
            "  macOS:  brew install pandoc\n"
            "  Ubuntu: sudo apt install pandoc\n"
            "  Windows: choco install pandoc / 或到 pandoc.org 下载"
        )
    return path


def find_chrome() -> str:
    """跨平台探测 Chrome / Chromium 可执行文件。"""
    env = os.environ.get("MD2PDF_CHROME")
    if env and os.path.isfile(env):
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "chrome", "microsoft-edge"):
        p = shutil.which(name)
        if p:
            return p
    raise BuildError(
        "未找到 Chrome / Chromium。请安装 Google Chrome,或用环境变量指定:\n"
        "  export MD2PDF_CHROME=/path/to/chrome"
    )


# --------------------------------------------------------------------------- #
# 链接收集
# --------------------------------------------------------------------------- #
def _md_link_targets(md_file: str, text: str) -> list[str]:
    """返回该文件内、按出现顺序排列、解析为绝对路径的本地 .md 链接目标(去重、存在)。"""
    base = os.path.dirname(md_file)
    out, seen = [], set()
    for m in _LINK_RE.finditer(text):
        target = m.group(1)
        if "://" in target or target.startswith(("#", "mailto:")):
            continue  # 外部链接 / 页内锚点,跳过
        if not target.lower().endswith(".md"):
            continue
        abs_target = os.path.normpath(os.path.join(base, target))
        if abs_target in seen:
            continue
        seen.add(abs_target)
        if os.path.isfile(abs_target):
            out.append(abs_target)
    return out


def collect_linked(main_file: str) -> list[str]:
    """从主文件出发,按链接顺序广度优先收集全部可达的本地 .md,返回有序去重列表。"""
    main_file = os.path.abspath(main_file)
    if not os.path.isfile(main_file):
        raise BuildError(f"主文件不存在:{main_file}")
    order = [main_file]
    seen = {main_file}
    queue = [main_file]
    while queue:
        cur = queue.pop(0)
        with open(cur, encoding="utf-8") as f:
            text = f.read()
        for tgt in _md_link_targets(cur, text):
            if tgt not in seen:
                seen.add(tgt)
                order.append(tgt)
                queue.append(tgt)
    return order


# --------------------------------------------------------------------------- #
# 合并 + 链接改写
# --------------------------------------------------------------------------- #
def _rewrite_links(md_file: str, text: str, id_of: dict[str, str]) -> str:
    """把指向「已收集文件」的 .md 链接改写成 PDF 内部锚点 #secN。"""
    base = os.path.dirname(md_file)

    def repl(m: re.Match) -> str:
        target = m.group(1)
        if "://" in target or not target.lower().endswith(".md"):
            return m.group(0)
        abs_target = os.path.normpath(os.path.join(base, target))
        sec = id_of.get(abs_target)
        return f"](#{sec})" if sec else m.group(0)

    return _LINK_RE.sub(repl, text)


def _derive_title(main_file: str) -> str:
    with open(main_file, encoding="utf-8") as f:
        text = f.read()
    m = _H1_RE.search(text)
    if m:
        return m.group(1).strip()
    return os.path.splitext(os.path.basename(main_file))[0]


def _combine(files: list[str]) -> str:
    id_of = {path: f"sec{i}" for i, path in enumerate(files)}
    parts = []
    for i, path in enumerate(files):
        with open(path, encoding="utf-8") as f:
            body = f.read()
        body = _rewrite_links(path, body, id_of)
        parts.append(f'\n\n<div id="sec{i}"></div>\n\n{body}')
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# 构建
# --------------------------------------------------------------------------- #
def build(
    main_file: str,
    output: str | None = None,
    toc: bool = True,
    css: str | None = None,
    title: str | None = None,
    verbose: bool = False,
) -> str:
    """把主文件及其关联 md 合并渲染成 PDF,返回输出路径。"""
    pandoc = find_pandoc()
    chrome = find_chrome()

    main_file = os.path.abspath(main_file)
    files = collect_linked(main_file)
    if title is None:
        title = _derive_title(main_file)
    if output is None:
        stem = os.path.splitext(os.path.basename(main_file))[0]
        output = os.path.join(os.path.dirname(main_file), stem + ".pdf")
    output = os.path.abspath(output)
    css = os.path.abspath(css) if css else DEFAULT_CSS

    def log(msg: str) -> None:
        if verbose:
            print(msg, file=sys.stderr)

    log(f"收集到 {len(files)} 个 Markdown 文件:")
    for p in files:
        log("  - " + os.path.relpath(p, os.path.dirname(main_file)))

    workdir = tempfile.mkdtemp(prefix="md2pdf_")
    try:
        combined_md = os.path.join(workdir, "combined.md")
        with open(combined_md, "w", encoding="utf-8") as f:
            f.write(_combine(files))

        header_html = os.path.join(workdir, "style_header.html")
        with open(css, encoding="utf-8") as f:
            css_text = f.read()
        with open(header_html, "w", encoding="utf-8") as f:
            f.write("<style>\n" + css_text + "\n</style>\n")

        html_path = os.path.join(workdir, "combined.html")
        pandoc_cmd = [
            pandoc, combined_md, "-o", html_path,
            "--standalone", "-f", PANDOC_FROM,
            "--include-in-header", header_html,
            "-V", f"pagetitle={title}",
            "-M", "lang=zh-CN",
        ]
        if toc:
            pandoc_cmd += ["--toc", "--toc-depth=2"]
        log("[pandoc] 生成 HTML …")
        r = subprocess.run(pandoc_cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise BuildError("pandoc 失败:\n" + r.stderr)

        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        chrome_cmd = [
            chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
            "--print-to-pdf=" + output, "file://" + html_path,
        ]
        log("[chrome] 打印 PDF …")
        subprocess.run(chrome_cmd, capture_output=True, text=True)
        if not os.path.isfile(output):
            raise BuildError("Chrome 未能生成 PDF(请确认 Chrome 可用)。")
        return output
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
