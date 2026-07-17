# -*- coding: utf-8 -*-
"""md2pdf 图形界面:把主 .md 拖进窗口(或点击选择),即可生成 PDF。

* 若安装了 tkinterdnd2,支持真正的「拖拽」;否则自动降级为「点击选择文件」。
* 默认在源文件同目录生成 PDF,也可指定输出路径。
* 导入本模块不会创建窗口;窗口只在 main() 中创建。
"""
from __future__ import annotations

import os
import threading


def _require_tk():
    """导入 tkinter,失败时给出可操作的提示。"""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as e:  # pragma: no cover - 取决于本机 Python 是否带 tk
        raise SystemExit(
            "无法加载 tkinter(GUI 依赖它):%s\n"
            "  macOS(homebrew):brew install python-tk\n"
            "  Ubuntu:        sudo apt install python3-tk\n"
            "  Windows:       官方 python.org 安装包默认自带\n"
            "命令行版本不需要 tkinter:  md2pdf <主文件.md>" % e
        )
    return tk, filedialog, messagebox, ttk


def main() -> int:
    tk, filedialog, messagebox, ttk = _require_tk()
    from .core import build, BuildError

    # 尝试启用拖拽(可选依赖)
    dnd_ok = False
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        dnd_ok = True
    except Exception:
        root = tk.Tk()

    root.title("md2pdf")
    root.geometry("560x420")
    root.minsize(480, 380)

    state = {"main_file": None, "output": None}

    pad = {"padx": 16, "pady": 6}
    ttk.Label(root, text="md2pdf", font=("Helvetica", 22, "bold")).pack(pady=(18, 0))
    ttk.Label(root, text="拖入主 Markdown(如 index.md),自动收集关联文件生成 PDF").pack()

    # 拖放区 / 点击选择区
    drop = tk.Label(
        root,
        text=("把主 .md 文件拖到这里\n\n(或点击选择)" if dnd_ok else "点击选择主 .md 文件"),
        relief="ridge", borderwidth=2, height=6,
        bg="#f0f4f8", fg="#334", cursor="hand2",
    )
    drop.pack(fill="x", **pad)

    file_var = tk.StringVar(value="尚未选择文件")
    ttk.Label(root, textvariable=file_var, foreground="#556").pack(**pad)

    # 选项
    opt = ttk.Frame(root)
    opt.pack(fill="x", **pad)
    toc_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(opt, text="生成目录(TOC)", variable=toc_var).grid(row=0, column=0, sticky="w")

    out_var = tk.StringVar(value="输出:源文件同目录、同名 .pdf")
    ttk.Label(root, textvariable=out_var, foreground="#556").pack(**pad)

    status = tk.StringVar(value="")
    status_lbl = ttk.Label(root, textvariable=status, foreground="#0b6fa4", wraplength=520)
    status_lbl.pack(**pad)

    def set_main(path: str) -> None:
        path = os.path.abspath(path)
        if not path.lower().endswith(".md"):
            messagebox.showwarning("md2pdf", "请选择一个 .md 文件作为主文件。")
            return
        state["main_file"] = path
        file_var.set("主文件:" + path)
        status.set("")

    def choose_file() -> None:
        p = filedialog.askopenfilename(
            title="选择主 Markdown 文件",
            filetypes=[("Markdown", "*.md"), ("所有文件", "*.*")],
        )
        if p:
            set_main(p)

    def choose_output() -> None:
        if not state["main_file"]:
            messagebox.showinfo("md2pdf", "请先选择主文件。")
            return
        p = filedialog.asksaveasfilename(
            title="另存 PDF 为",
            defaultextension=".pdf",
            initialfile=os.path.splitext(os.path.basename(state["main_file"]))[0] + ".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if p:
            state["output"] = p
            out_var.set("输出:" + p)

    def do_build() -> None:
        if not state["main_file"]:
            messagebox.showinfo("md2pdf", "请先拖入或选择主 .md 文件。")
            return
        status.set("正在生成 …")
        gen_btn.config(state="disabled")

        def worker() -> None:
            try:
                out = build(state["main_file"], output=state["output"],
                            toc=toc_var.get(), verbose=False)
                root.after(0, done, out, None)
            except BuildError as e:
                root.after(0, done, None, str(e))
            except Exception as e:  # pragma: no cover
                root.after(0, done, None, repr(e))

        threading.Thread(target=worker, daemon=True).start()

    def done(out: str | None, err: str | None) -> None:
        gen_btn.config(state="normal")
        if err:
            status.set("失败:" + err)
            messagebox.showerror("md2pdf", err)
        else:
            status.set("✓ 已生成:" + out)
            messagebox.showinfo("md2pdf", "已生成:\n" + out)

    drop.bind("<Button-1>", lambda e: choose_file())
    if dnd_ok:
        def on_drop(event):
            # tkinterdnd2 会把多个文件用空格拼接、路径可能带 {}
            data = event.data.strip()
            if data.startswith("{") and data.endswith("}"):
                data = data[1:-1]
            set_main(data.split("} {")[0].strip("{}"))
        drop.drop_target_register(DND_FILES)
        drop.dnd_bind("<<Drop>>", on_drop)

    btns = ttk.Frame(root)
    btns.pack(pady=(2, 12))
    ttk.Button(btns, text="选择输出路径…", command=choose_output).grid(row=0, column=0, padx=6)
    gen_btn = ttk.Button(btns, text="生成 PDF", command=do_build)
    gen_btn.grid(row=0, column=1, padx=6)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
