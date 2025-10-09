import sys
import pandas as pd
import os
from datetime import datetime

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit,
                             QFileDialog, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal


class ExcelMerger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Excel 文件合并工具")
        self.setGeometry(100, 100, 600, 500)
        self.setWindowIcon(QIcon('icon.ico'))
        # 主控件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()

        # 输入控件
        self.folder_label = QLabel("Excel文件所在文件夹:")
        self.folder_input = QLineEdit()
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_folder)

        self.sheet_label = QLabel("工作表名称（留空自动获取第一个sheet）:")
        self.sheet_input = QLineEdit()

        self.header_label = QLabel("表头行数（默认3行）:")
        self.header_input = QLineEdit("3")

        self.chunk_label = QLabel("分块大小（行数，默认5000）:")
        self.chunk_input = QLineEdit("5000")

        # 日志输出
        self.log_label = QLabel("操作日志:")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # 合并按钮
        self.merge_button = QPushButton("开始合并")
        self.merge_button.clicked.connect(self.start_merge)

        # 添加到布局
        self.layout.addWidget(self.folder_label)
        self.layout.addWidget(self.folder_input)
        self.layout.addWidget(self.browse_button)
        self.layout.addWidget(self.sheet_label)
        self.layout.addWidget(self.sheet_input)
        self.layout.addWidget(self.header_label)
        self.layout.addWidget(self.header_input)
        self.layout.addWidget(self.chunk_label)
        self.layout.addWidget(self.chunk_input)
        self.layout.addWidget(self.log_label)
        self.layout.addWidget(self.log_output)
        self.layout.addWidget(self.merge_button)

        self.central_widget.setLayout(self.layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.folder_input.setText(folder)

    def log_message(self, message):
        self.log_output.append(message)
        QApplication.processEvents()  # 确保UI实时更新

    def start_merge(self):
        # 获取输入参数
        input_folder = self.folder_input.text()
        sheet_name = self.sheet_input.text()
        try:
            header_rows = int(self.header_input.text())
            chunk_size = int(self.chunk_input.text())
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数字")
            return

        if not os.path.exists(input_folder):
            QMessageBox.warning(self, "路径错误", "文件夹不存在！")
            return

        # 创建工作线程
        self.worker = MergeWorker(input_folder, sheet_name, header_rows, chunk_size)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.merge_complete)
        self.worker.start()

        self.merge_button.setEnabled(False)

    def merge_complete(self, success, output_file):
        self.merge_button.setEnabled(True)
        if success:
            self.log_message(f"\n✅ 合并完成！文件已保存到: {output_file}")
            QMessageBox.information(self, "完成", f"合并完成！\n输出文件: {output_file}")
        else:
            QMessageBox.critical(self, "错误", "合并过程中出现错误，请查看日志")


class MergeWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, input_folder, sheet_name, header_rows, chunk_size):
        super().__init__()
        self.input_folder = input_folder
        self.sheet_name = sheet_name
        self.header_rows = header_rows
        self.chunk_size = chunk_size
        self.output_file = ""

    def run(self):
        try:
            self.log_signal.emit("=== 开始合并Excel文件 ===")

            # 获取所有Excel文件
            files = sorted([f for f in os.listdir(self.input_folder)
                            if f.lower().endswith(('.xlsx', '.xls')) and not f.startswith('~$')])

            if not files:
                self.log_signal.emit("错误：未找到Excel文件！")
                self.finished_signal.emit(False, "")
                return

            self.log_signal.emit(f"找到 {len(files)} 个文件，开始合并...")

            # 自动生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file = os.path.join(self.input_folder, f"合并结果_{timestamp}.xlsx")

            # 获取第一个文件的表头
            first_file = os.path.join(self.input_folder, files[0])
            if not self.sheet_name:
                with pd.ExcelFile(first_file) as xls:
                    self.sheet_name = xls.sheet_names[0]
                    self.log_signal.emit(f"自动获取工作表名称: {self.sheet_name}")

            header = pd.read_excel(first_file, nrows=self.header_rows, header=None)

            # 初始化Excel写入器
            with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
                # 不写入表头
                # header.to_excel(writer, sheet_name=self.sheet_name, index=False, header=False)
                current_row = 0

                # 处理每个文件
                for i, file in enumerate(files, 1):
                    file_path = os.path.join(self.input_folder, file)
                    self.log_signal.emit(f"正在处理文件 {i}/{len(files)}: {file}")

                    # 读取整个文件（跳过表头）
                    full_data = pd.read_excel(
                        file_path,
                        skiprows=self.header_rows,
                        header=None,
                        dtype=str
                    )

                    # 手动分块处理
                    for chunk_start in range(0, len(full_data), self.chunk_size):
                        chunk = full_data.iloc[chunk_start:chunk_start + self.chunk_size]
                        chunk.to_excel(
                            writer,
                            sheet_name=self.sheet_name,
                            startrow=current_row,
                            index=False,
                            header=False
                        )
                        current_row += len(chunk)
                        self.log_signal.emit(f"已写入 {current_row} 行数据...")

            self.log_signal.emit("\n合并统计:")
            self.log_signal.emit(f"工作表名称: {self.sheet_name}")
            self.log_signal.emit(f"表头行数: {self.header_rows}")
            self.log_signal.emit(f"总文件数: {len(files)}")
            self.log_signal.emit(f"总数据行数: {current_row}")

            self.finished_signal.emit(True, self.output_file)

        except Exception as e:
            self.log_signal.emit(f"\n❌ 错误: {str(e)}")
            if hasattr(self, 'output_file') and os.path.exists(self.output_file):
                os.remove(self.output_file)
                self.log_signal.emit("已删除不完整的输出文件")
            self.finished_signal.emit(False, "")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExcelMerger()
    window.show()
    sys.exit(app.exec())
