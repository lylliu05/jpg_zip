import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import os
import threading
import time
from queue import Queue
import functools


def debounce(wait):
    """
    防抖装饰器，用于延迟函数执行
    """
    def decorator(func):
        @functools.wraps(func)
        def debounced(*args, **kwargs):
            def call_it():
                func(*args, **kwargs)
            try:
                debounced.timer.cancel()
            except (AttributeError, NameError):
                pass
            debounced.timer = threading.Timer(wait, call_it)
            debounced.timer.start()
        return debounced
    return decorator


def compress_image(input_path, output_path, quality=80):
    """
    压缩单个图片文件
    """
    try:
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
            img.save(output_path, optimize=True, quality=quality)
        return os.path.getsize(output_path)
    except Exception as e:
        print(f"处理 {input_path} 时出错: {e}")
        return 0


def generate_temp_file_path():
    """
    生成唯一的临时文件路径
    """
    temp_timestamp = str(int(time.time() * 1000))
    return f"temp_compressed_{temp_timestamp}.jpg"


def estimate_file_size(file_path, quality):
    """
    预估单个文件压缩后的大小
    """
    try:
        with Image.open(file_path) as img:
            temp_output = generate_temp_file_path()
            img.save(temp_output, optimize=True, quality=quality)
            size = os.path.getsize(temp_output)
            os.remove(temp_output)
            return size
    except Exception as e:
        print(f"预估 {file_path} 大小时出错: {e}")
        return 0


def estimate_folder_size(folder_path, quality, output_queue):
    """
    异步预估文件夹内所有图片文件压缩后的总大小
    """
    total_size = 0
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(root, file)
                    size = estimate_file_size(file_path, quality)
                    total_size += size
    except Exception as e:
        print(f"预估文件夹 {folder_path} 大小时出错: {e}")
    output_queue.put(total_size)


def format_size(size):
    """
    将字节转换为 KB 或 MB 格式
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size / (1024 ** 2):.2f} MB"


class ImageCompressorApp:
    def __init__(self, master):
        self.master = master
        master.title("图片压缩工具")

        # 初始化变量
        self.selected_path = ""
        self.mode = tk.StringVar(value="file")
        self.quality = tk.IntVar(value=30)
        self.output_queue = Queue()

        # 创建界面组件
        self.create_widgets()

    def create_widgets(self):
        # 模式选择部分
        mode_frame = ttk.LabelFrame(self.master, text="选择模式")
        mode_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        ttk.Radiobutton(mode_frame, text="单个文件", variable=self.mode, value="file",
                        command=self.update_ui).grid(row=0, column=0, padx=10)
        ttk.Radiobutton(mode_frame, text="文件夹（批量模式）", variable=self.mode, value="folder",
                        command=self.update_ui).grid(row=0, column=1, padx=10)

        # 路径选择部分
        path_frame = ttk.LabelFrame(self.master, text="选择路径")
        path_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.path_entry = ttk.Entry(path_frame, width=50)
        self.path_entry.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        ttk.Button(path_frame, text="选择路径", command=self.select_path).grid(row=0, column=1, padx=10, pady=5)

        # 压缩质量选择部分
        quality_frame = ttk.LabelFrame(self.master, text="选择压缩质量 (0 - 100)")
        quality_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        quality_scale = ttk.Scale(quality_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                  variable=self.quality, command=self.debounced_update_estimated_size)
        quality_scale.set(30)
        quality_scale.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.quality_label = ttk.Label(quality_frame, text=f"当前质量: {self.quality.get()}")
        self.quality_label.grid(row=0, column=1, padx=10, pady=5)

        # 显示预估大小的标签
        self.size_label = ttk.Label(self.master, text="请选择文件或文件夹")
        self.size_label.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        # 进度条
        self.progress = ttk.Progressbar(self.master, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # 开始压缩按钮
        ttk.Button(self.master, text="开始压缩", command=self.start_compression).grid(row=5, column=0, columnspan=2,
                                                                                      padx=10, pady=10)

    def update_ui(self):
        """
        更新界面状态
        """
        self.path_entry.delete(0, tk.END)
        self.size_label.config(text="请选择文件或文件夹")
        self.progress["value"] = 0

    def select_path(self):
        """
        选择文件或文件夹路径
        """
        if self.mode.get() == "file":
            path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png")])
        else:
            path = filedialog.askdirectory()
        if path:
            self.selected_path = path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.debounced_update_estimated_size()

    @debounce(0.5)
    def debounced_update_estimated_size(self, _=None):
        """
        防抖更新预估大小
        """
        self.update_estimated_size()

    def update_estimated_size(self):
        """
        更新预估大小
        """
        quality = self.quality.get()
        self.quality_label.config(text=f"当前质量: {quality}")
        if not self.selected_path:
            self.size_label.config(text="请选择文件或文件夹")
            return
        if self.mode.get() == "file":
            size = estimate_file_size(self.selected_path, quality)
            self.size_label.config(text=f"预估压缩后文件大小: {format_size(size)}")
        else:
            self.size_label.config(text="正在预估文件夹内文件大小...")
            threading.Thread(target=estimate_folder_size, args=(self.selected_path, quality, self.output_queue),
                             daemon=True).start()
            self.master.after(100, self.check_estimate_result)

    def check_estimate_result(self):
        """
        检查异步预估结果
        """
        if not self.output_queue.empty():
            total_size = self.output_queue.get()
            self.size_label.config(text=f"预估所有压缩后文件总大小: {format_size(total_size)}")
        else:
            self.master.after(100, self.check_estimate_result)

    def start_compression(self):
        """
        开始压缩任务
        """
        quality = self.quality.get()
        if not self.selected_path:
            messagebox.showerror("错误", "请选择文件或文件夹")
            return
        if self.mode.get() == "file":
            output_dir = os.path.dirname(self.selected_path)
            file_name = os.path.basename(self.selected_path)
            output_file = os.path.join(output_dir, f"compressed_{file_name}")
            compressed_size = compress_image(self.selected_path, output_file, quality)
            if compressed_size > 0:
                messagebox.showinfo("完成", f"单个文件压缩完成，压缩后文件大小: {format_size(compressed_size)}")
            else:
                messagebox.showerror("错误", "文件压缩失败")
        else:
            image_files = []
            total_compressed_size = 0
            for root, dirs, files in os.walk(self.selected_path):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        image_files.append(os.path.join(root, file))
            self.progress["maximum"] = len(image_files)
            self.progress["value"] = 0
            for i, input_path in enumerate(image_files):
                output_dir = os.path.dirname(input_path)
                file_name = os.path.basename(input_path)
                output_file = os.path.join(output_dir, f"compressed_{file_name}")
                compressed_size = compress_image(input_path, output_file, quality)
                total_compressed_size += compressed_size
                self.progress["value"] = i + 1
                self.master.update_idletasks()
            messagebox.showinfo("完成", f"批量压缩完成，所有压缩后文件总大小: {format_size(total_compressed_size)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCompressorApp(root)
    root.mainloop()
    