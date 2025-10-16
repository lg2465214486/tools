import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import html2text
import os
import chardet


class HTMLToMDConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("HTML转Markdown工具 - 编码修复版")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.create_widgets()
        self.check_dependencies()

    def check_dependencies(self):
        """检查并安装依赖"""
        try:
            import html2text
            import chardet
        except ImportError as e:
            if messagebox.askyesno("安装依赖", "需要安装依赖库，是否立即安装？"):
                self.install_dependencies()
            else:
                messagebox.showerror("错误", "缺少必要依赖库，程序无法运行")
                self.root.quit()

    def install_dependencies(self):
        """安装依赖库"""
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "html2text", "chardet"])
            messagebox.showinfo("成功", "依赖库安装完成，请重新启动程序")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("错误", f"安装依赖失败: {str(e)}")
            self.root.quit()

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="HTML转Markdown工具 - 编码修复版", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 15))

        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="HTML输入", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # HTML输入文本框
        self.html_text = scrolledtext.ScrolledText(input_frame, height=10, wrap=tk.WORD)
        self.html_text.pack(fill=tk.BOTH, expand=True)

        # 编码设置区域
        encoding_frame = ttk.Frame(main_frame)
        encoding_frame.pack(fill=tk.X, pady=5)

        ttk.Label(encoding_frame, text="HTML文件编码:").pack(side=tk.LEFT)
        self.html_encoding_var = tk.StringVar(value="auto")
        html_encoding_combo = ttk.Combobox(encoding_frame, textvariable=self.html_encoding_var,
                                           values=["auto", "utf-8", "gbk", "gb2312", "big5", "latin-1"],
                                           width=10, state="readonly")
        html_encoding_combo.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(encoding_frame, text="MD文件编码:").pack(side=tk.LEFT)
        self.md_encoding_var = tk.StringVar(value="utf-8")
        md_encoding_combo = ttk.Combobox(encoding_frame, textvariable=self.md_encoding_var,
                                         values=["utf-8", "gbk", "utf-8-sig"],
                                         width=10, state="readonly")
        md_encoding_combo.pack(side=tk.LEFT, padx=(5, 0))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        # 加载HTML文件按钮
        load_button = ttk.Button(button_frame, text="加载HTML文件", command=self.load_html_file)
        load_button.pack(side=tk.LEFT, padx=(0, 10))

        # 清空按钮
        clear_button = ttk.Button(button_frame, text="清空内容", command=self.clear_content)
        clear_button.pack(side=tk.LEFT, padx=(0, 10))

        # 转换按钮
        convert_button = ttk.Button(button_frame, text="转换为Markdown", command=self.convert_to_md)
        convert_button.pack(side=tk.LEFT, padx=(0, 10))

        # 保存按钮
        save_button = ttk.Button(button_frame, text="保存Markdown", command=self.save_md_file)
        save_button.pack(side=tk.LEFT)

        # 输出区域
        output_frame = ttk.LabelFrame(main_frame, text="Markdown输出", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)

        # Markdown输出文本框
        self.md_text = scrolledtext.ScrolledText(output_frame, height=15, wrap=tk.WORD)
        self.md_text.pack(fill=tk.BOTH, expand=True)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def detect_encoding(self, file_path):
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # 读取前10000字节进行检测
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                return encoding, confidence
        except Exception as e:
            return 'utf-8', 0

    def load_html_file(self):
        file_path = filedialog.askopenfilename(
            title="选择HTML文件",
            filetypes=[("HTML文件", "*.html *.htm"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                encoding = self.html_encoding_var.get()

                if encoding == "auto":
                    # 自动检测编码
                    detected_encoding, confidence = self.detect_encoding(file_path)
                    if detected_encoding and confidence > 0.6:
                        encoding = detected_encoding
                        self.status_var.set(f"检测到编码: {detected_encoding} (置信度: {confidence:.2f})")
                    else:
                        encoding = 'utf-8'
                        self.status_var.set("使用默认编码: utf-8")

                # 尝试读取文件
                try:
                    with open(file_path, 'r', encoding=encoding, errors='replace') as file:
                        html_content = file.read()
                except UnicodeDecodeError:
                    # 如果第一次尝试失败，尝试其他常见编码
                    for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                        if enc != encoding:
                            try:
                                with open(file_path, 'r', encoding=enc, errors='replace') as file:
                                    html_content = file.read()
                                encoding = enc
                                self.status_var.set(f"重新检测编码为: {enc}")
                                break
                            except UnicodeDecodeError:
                                continue
                    else:
                        raise UnicodeDecodeError("无法找到合适的编码")

                self.html_text.delete(1.0, tk.END)
                self.html_text.insert(tk.END, html_content)
                self.status_var.set(f"已加载文件: {os.path.basename(file_path)} (编码: {encoding})")

            except Exception as e:
                messagebox.showerror("错误", f"读取文件时出错: {str(e)}\n请尝试手动选择正确的编码")

    def clear_content(self):
        self.html_text.delete(1.0, tk.END)
        self.md_text.delete(1.0, tk.END)
        self.status_var.set("内容已清空")

    def convert_to_md(self):
        html_content = self.html_text.get(1.0, tk.END).strip()

        if not html_content:
            messagebox.showwarning("警告", "请输入HTML内容")
            return

        try:
            # 创建html2text转换器
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0  # 不限制行宽

            # 转换HTML为Markdown
            md_content = h.handle(html_content)

            # 显示转换结果
            self.md_text.delete(1.0, tk.END)
            self.md_text.insert(tk.END, md_content)

            self.status_var.set("转换完成")
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中出错: {str(e)}")

    def save_md_file(self):
        md_content = self.md_text.get(1.0, tk.END).strip()

        if not md_content:
            messagebox.showwarning("警告", "没有可保存的Markdown内容")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存Markdown文件",
            defaultextension=".md",
            filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                encoding = self.md_encoding_var.get()
                with open(file_path, 'w', encoding=encoding, errors='replace') as file:
                    file.write(md_content)
                self.status_var.set(f"文件已保存: {os.path.basename(file_path)} (编码: {encoding})")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")


def main():
    root = tk.Tk()
    app = HTMLToMDConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
