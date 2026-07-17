# -*- coding: utf-8 -*-
"""md2pdf —— 给一个主 Markdown 文件,自动收集其关联的 .md 并生成单个 PDF。"""
from .core import build, collect_linked, BuildError

__version__ = "1.0.0"
__all__ = ["build", "collect_linked", "BuildError", "__version__"]
