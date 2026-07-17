# md2pdf

> 给一个**主 Markdown 文件**(如 `index.md`),它会**自动顺着链接收集所有关联的 `.md`**,
> 合并成一本带目录、可跳转、中文正常显示的 **单个 PDF**。命令行、拖拽 GUI 皆可。

面向「用一堆互相链接的 Markdown 写成的文档/教程/笔记」——你不需要手动列出每一章,
只要指向入口文件,`md2pdf` 会自己把整本书拼出来。

## 特性

- **一个入口,自动成书**:从主文件出发做广度优先遍历,按链接出现顺序收集全部可达的本地 `.md`,天然得到「目录 → 各章」的阅读顺序。
- **跨文件跳转不丢**:合并成单文件后,原来 `[..](other.md)` 的链接会改写成 PDF 内部锚点,依然能点。
- **中文/CJK 稳定**:用 Chrome 无头打印,字体、分页、页码都正常(不用会丢字的 weasyprint)。
- **自带排版**:内置一套干净的样式(代码块、表格、页码…),也可 `--css` 换成自己的。
- **两种用法**:命令行 `md2pdf index.md`;或拖拽 GUI,把主文件拖进去即可。
- **零 Python 硬依赖**:核心只用标准库;拖拽是可选增强。

## 工作原理

```
主文件 index.md
   │  ① 顺着 ](*.md) 链接 BFS 收集全部关联 md(去重、保序)
   │  ② 每个文件前插入锚点,跨文件链接改写为 #内部锚点
   ▼
合并后的 Markdown
   │  ③ pandoc → 独立 HTML(内嵌 CSS,生成目录)
   ▼
   HTML
   │  ④ Chrome --headless --print-to-pdf
   ▼
  单个 PDF(带书签目录、中文正常、可跳转)
```

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| **pandoc** | Markdown → HTML | macOS `brew install pandoc` · Ubuntu `sudo apt install pandoc` · Windows `choco install pandoc` |
| **Google Chrome / Chromium** | HTML → PDF | 装好即可;或用 `MD2PDF_CHROME=/path/to/chrome` 指定 |
| **Python ≥ 3.8** | 运行本工具 | — |
| tkinter | GUI(可选) | macOS `brew install python-tk` · Ubuntu `sudo apt install python3-tk` · Windows 自带 |
| tkinterdnd2 | GUI 拖拽(可选) | `pip install tkinterdnd2`(不装则 GUI 降级为「点击选择」) |

## 安装

```bash
git clone https://github.com/zhtinist/md2pdf.git
cd md2pdf
pip install .            # 安装后可用 md2pdf / md2pdf-gui 命令
# 或者不安装,直接用源码:python -m md2pdf.cli index.md
```

## 命令行用法

```bash
md2pdf <主文件.md> [选项]
```

| 选项 | 说明 |
|------|------|
| `-o, --output PATH` | 输出 PDF 路径(默认:主文件同目录、同名 `.pdf`) |
| `--title TEXT`      | 文档标题(默认取主文件第一个一级标题) |
| `--css PATH`        | 自定义 CSS |
| `--no-toc`          | 不生成目录 |
| `-q, --quiet`       | 安静模式 |

例:

```bash
# 在同目录生成 index.pdf
md2pdf docs/index.md

# 指定输出路径
md2pdf docs/index.md -o ~/Desktop/手册.pdf
```

## 拖拽 GUI

```bash
md2pdf-gui          # 或:python -m md2pdf.gui
```

把主 `.md` 拖进窗口(未装 `tkinterdnd2` 时点击选择),默认在源文件同目录生成 PDF,
也可点「选择输出路径…」另存到别处。

## 库调用

```python
from md2pdf import build
build("docs/index.md", output="out.pdf", toc=True)
```

## 两个已知坑(已在内部规避)

1. **不要用 weasyprint 当 PDF 引擎**——它在 macOS/CoreGraphics 下渲染 CJK 会丢字,故本项目用 Chrome。
2. **pandoc 的 `simple_tables` / `multiline_tables` 扩展已关闭**——否则「一行 `---` 紧跟一行文字」会被误判成简单表格,吞掉后面的标题和正文;正文里的真实表格请用 `|` 竖线表格(`pipe_table`)。

## 许可证

[MIT](LICENSE) © HTZHU
