import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import json
import os
import gc
from threading import Thread
import time


class LargeJSONFormatter:
    def __init__(self, root):
        self.root = root
        self.root.title("大文件JSON格式化工具")
        self.root.geometry("700x600")

        # 处理状态变量
        self.is_processing = False
        self.progress = 0

        self.create_widgets()

    def create_widgets(self):
        # 主框架
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 输入文件选择
        input_frame = tk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        tk.Label(input_frame, text="输入文件:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.input_entry = tk.Entry(input_frame, width=60)
        self.input_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        tk.Button(input_frame, text="浏览", command=self.browse_input_file, width=8).pack(side=tk.LEFT)

        # 输出文件选择
        output_frame = tk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=5)

        tk.Label(output_frame, text="输出文件:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.output_entry = tk.Entry(output_frame, width=60)
        self.output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        tk.Button(output_frame, text="浏览", command=self.browse_output_file, width=8).pack(side=tk.LEFT)

        # 选项框架
        options_frame = tk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=10)

        self.compact_var = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="紧凑模式 (减少空格)", variable=self.compact_var).pack(side=tk.LEFT)

        self.ensure_ascii_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="确保ASCII输出(中文会变成unicode编码)", variable=self.ensure_ascii_var).pack(side=tk.LEFT, padx=20)

        # 进度条
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = tk.Label(progress_frame, text="就绪")
        self.progress_label.pack()

        # 操作按钮
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=10)

        self.format_btn = tk.Button(button_frame, text="格式化JSON", command=self.start_format_thread,
                                    bg="lightblue", width=15, font=("Arial", 10))
        self.format_btn.pack(side=tk.LEFT, padx=5)

        self.validate_btn = tk.Button(button_frame, text="验证JSON", command=self.validate_json,
                                      bg="lightgreen", width=15, font=("Arial", 10))
        self.validate_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="清空", command=self.clear_all,
                  bg="lightcoral", width=15, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        # 文件信息
        info_frame = tk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)

        self.info_label = tk.Label(info_frame, text="", font=("Arial", 9), fg="gray")
        self.info_label.pack()

        # 预览区域
        preview_frame = tk.LabelFrame(main_frame, text="预览 (前5000字符)")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=15, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="选择输入文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filename:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filename)
            self.update_file_info(filename)

            # 自动生成输出文件名
            input_path = self.input_entry.get()
            if input_path:
                dir_name = os.path.dirname(input_path)
                file_name = os.path.basename(input_path)
                name, ext = os.path.splitext(file_name)
                output_name = f"{name}_formatted{ext}"
                output_path = os.path.join(dir_name, output_name)
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, output_path)

    def browse_output_file(self):
        filename = filedialog.asksaveasfilename(
            title="选择输出文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filename)

    def update_file_info(self, filename):
        try:
            file_size = os.path.getsize(filename)
            size_mb = file_size / (1024 * 1024)
            self.info_label.config(text=f"文件大小: {size_mb:.2f} MB")
        except:
            self.info_label.config(text="无法获取文件信息")

    def update_progress(self, value, text=""):
        self.progress_bar['value'] = value
        if text:
            self.progress_label.config(text=text)
        self.root.update_idletasks()

    def validate_json(self):
        input_file = self.input_entry.get()
        if not input_file:
            messagebox.showerror("错误", "请选择输入文件")
            return

        try:
            self.update_progress(0, "验证JSON文件中...")

            # 对于大文件，只验证前几MB来检查基本结构
            with open(input_file, 'r', encoding='utf-8') as f:
                sample_data = f.read(1024 * 1024)  # 读取1MB进行验证

            try:
                json.loads(sample_data + "\n]}" if not sample_data.strip().endswith((']', '}')) else sample_data)
                messagebox.showinfo("成功", "JSON文件格式基本正确")
            except json.JSONDecodeError as e:
                messagebox.showerror("错误", f"JSON格式错误: {str(e)}")

        except Exception as e:
            messagebox.showerror("错误", f"验证文件时出错: {str(e)}")
        finally:
            self.update_progress(0, "就绪")

    def format_json_streaming(self, input_file, output_file):
        """使用流式处理格式化大JSON文件"""
        try:
            self.update_progress(10, "读取输入文件...")

            # 读取整个文件（对于特大文件，可以改为分块读取）
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()

            self.update_progress(30, "解析JSON数据...")

            # 解析JSON
            data = json.loads(content)

            self.update_progress(60, "格式化并写入文件...")

            # 确定缩进参数
            indent = None if self.compact_var.get() else 4

            # 写入格式化后的JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=self.ensure_ascii_var.get())

            self.update_progress(90, "清理内存...")

            # 清理内存
            del data, content
            gc.collect()

            self.update_progress(100, "完成!")

            # 显示预览
            self.show_preview(output_file)

            return True, "格式化完成"

        except MemoryError:
            return False, "内存不足，文件太大"
        except json.JSONDecodeError as e:
            return False, f"JSON解析错误: {str(e)}"
        except Exception as e:
            return False, f"处理文件时出错: {str(e)}"

    def format_json_chunked(self, input_file, output_file):
        """分块处理特大JSON文件（适用于数组形式的JSON）"""
        try:
            self.update_progress(10, "准备分块处理...")

            # 这种方法适用于JSON数组，逐行处理
            with open(input_file, 'r', encoding='utf-8') as infile, \
                    open(output_file, 'w', encoding='utf-8') as outfile:

                # 写入开头的括号
                first_char = infile.read(1)
                outfile.write(first_char)

                if first_char == '[':
                    # 处理数组
                    self.process_json_array(infile, outfile)
                else:
                    # 对于对象，使用标准方法
                    infile.seek(0)
                    content = infile.read()
                    data = json.loads(content)
                    json.dump(data, outfile, indent=4, ensure_ascii=self.ensure_ascii_var.get())

            self.update_progress(100, "完成!")
            self.show_preview(output_file)
            return True, "格式化完成"

        except Exception as e:
            return False, f"分块处理失败: {str(e)}"

    def process_json_array(self, infile, outfile):
        """处理JSON数组的分块格式化"""
        buffer = ""
        line_count = 0
        indent = " " * 4

        while True:
            chunk = infile.read(8192)  # 8KB chunks
            if not chunk:
                break

            buffer += chunk

            # 处理缓冲区中的完整JSON对象
            while True:
                # 查找完整的JSON对象（以}结尾的行）
                end_pos = buffer.find('}\n')
                if end_pos == -1:
                    end_pos = buffer.find('},')
                if end_pos == -1:
                    break

                # 提取并格式化一个完整的对象
                obj_str = buffer[:end_pos + 1]
                buffer = buffer[end_pos + 2:]

                try:
                    obj = json.loads(obj_str)
                    formatted = json.dumps(obj, indent=4, ensure_ascii=self.ensure_ascii_var.get())
                    if line_count > 0:
                        outfile.write(",\n" + formatted)
                    else:
                        outfile.write("\n" + formatted)
                    line_count += 1
                except:
                    # 如果解析失败，按原样写入
                    if line_count > 0:
                        outfile.write(",\n" + obj_str)
                    else:
                        outfile.write("\n" + obj_str)
                    line_count += 1

                self.update_progress(10 + (line_count % 90), f"已处理 {line_count} 个对象...")

        # 写入剩余内容
        if buffer.strip():
            outfile.write(buffer)

        # 写入结尾
        outfile.write("\n]")

    def show_preview(self, output_file):
        """显示输出文件的前1000字符作为预览"""
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                preview_content = f.read(10000)

            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, preview_content)

            file_size = os.path.getsize(output_file)
            size_mb = file_size / (1024 * 1024)
            self.info_label.config(text=f"输出文件大小: {size_mb:.2f} MB")

        except Exception as e:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, f"预览失败: {str(e)}")

    def start_format_thread(self):
        """在新线程中执行格式化操作"""
        if self.is_processing:
            return

        input_file = self.input_entry.get()
        output_file = self.output_entry.get()

        if not input_file or not output_file:
            messagebox.showerror("错误", "请选择输入和输出文件")
            return

        # 检查输入文件大小
        try:
            file_size = os.path.getsize(input_file)
            if file_size > 500 * 1024 * 1024:  # 500MB以上
                response = messagebox.askyesno(
                    "大文件警告",
                    f"文件大小: {file_size / (1024 * 1024):.1f}MB\n这可能会消耗大量内存和时间。是否继续？"
                )
                if not response:
                    return
        except:
            pass

        self.is_processing = True
        self.format_btn.config(state=tk.DISABLED, text="处理中...")
        self.validate_btn.config(state=tk.DISABLED)

        # 在新线程中执行格式化
        thread = Thread(target=self.format_in_thread, args=(input_file, output_file))
        thread.daemon = True
        thread.start()

    def format_in_thread(self, input_file, output_file):
        """在后台线程中执行格式化"""
        try:
            # 根据文件大小选择处理方法
            file_size = os.path.getsize(input_file)

            if file_size > 100 * 1024 * 1024:  # 100MB以上使用分块处理
                success, message = self.format_json_chunked(input_file, output_file)
            else:
                success, message = self.format_json_streaming(input_file, output_file)

            # 在主线程中显示结果
            self.root.after(0, lambda: self.format_complete(success, message))

        except Exception as e:
            self.root.after(0, lambda: self.format_complete(False, f"处理失败: {str(e)}"))

    def format_complete(self, success, message):
        """格式化完成后的回调"""
        self.is_processing = False
        self.format_btn.config(state=tk.NORMAL, text="格式化JSON")
        self.validate_btn.config(state=tk.NORMAL)

        if success:
            messagebox.showinfo("成功", message)
        else:
            messagebox.showerror("错误", message)

        self.update_progress(0, "就绪")

    def clear_all(self):
        self.input_entry.delete(0, tk.END)
        self.output_entry.delete(0, tk.END)
        self.preview_text.delete(1.0, tk.END)
        self.info_label.config(text="")
        self.update_progress(0, "就绪")


def main():
    root = tk.Tk()
    app = LargeJSONFormatter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
