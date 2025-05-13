import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys

# 检查必要依赖
try:
    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor
    from core import *
    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    MISSING_DEPENDENCY = str(e)

class MissingDependencyDialog:
    """显示缺失依赖的对话框"""
    def __init__(self, root):
        self.root = root
        self.root.title("缺少必要依赖")
        
        ttk.Label(
            self.root, 
            text="运行此程序需要安装以下依赖:",
            padding=10
        ).pack()
        
        ttk.Label(
            self.root, 
            text=MISSING_DEPENDENCY,
            padding=10,
            foreground="red"
        ).pack()
        
        ttk.Label(
            self.root, 
            text="请使用以下命令安装:",
            padding=10
        ).pack()
        
        install_cmd = "pip install pillow"
        ttk.Label(
            self.root, 
            text=install_cmd,
            padding=10,
            foreground="blue"
        ).pack()
        
        ttk.Button(
            self.root,
            text="退出",
            command=self.root.quit
        ).pack(pady=10)

class ImageCompressorUI:
    def __init__(self, master):
        if not HAS_DEPENDENCIES:
            MissingDependencyDialog(master)
            return
            
        self.master = master
        master.title("图片压缩工具")
        master.resizable(True, False)
        
        # 设置窗口图标
        try:
            master.iconbitmap(default='icon.ico')
        except:
            pass
        
        # 初始化变量
        self.selected_path = ""
        self.output_path = ""
        self.mode = tk.StringVar(value="file")
        self.quality = tk.IntVar(value=15)  # 降低默认质量到15
        self.output_queue = Queue()
        self.executor = ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1))
        self.is_compressing = False
        self.extreme_compression = tk.BooleanVar(value=False)
        
        # 创建界面组件
        self.create_widgets()
        
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于图片压缩工具",
            "图片压缩工具 v1.1.1\n\n"
            "功能：\n"
            "- 支持JPG/PNG图片压缩\n"
            "- 可调节压缩质量\n"
            "- 支持批量处理\n\n"
            "发布页面:\n"
            "gitee.com/lylliu05/jpg_zip\n\n"
            "作者: lylliu05"
        )

    def create_widgets(self):
        # 添加菜单栏
        menubar = tk.Menu(self.master)
        menubar.add_command(label="关于", command=self.show_about)
        self.master.config(menu=menubar)
        
        # 创建主框架
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 模式选择部分
        mode_frame = ttk.LabelFrame(main_frame, text="选择模式")
        mode_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Radiobutton(mode_frame, text="单个文件", variable=self.mode, value="file",
                       command=self.update_ui).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ttk.Radiobutton(mode_frame, text="文件夹（批量模式）", variable=self.mode, value="folder",
                       command=self.update_ui).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # 输入路径选择部分
        input_frame = ttk.LabelFrame(main_frame, text="选择输入路径")
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        input_path_frame = ttk.Frame(input_frame)
        input_path_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        self.input_entry = ttk.Entry(input_path_frame, width=50)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(input_path_frame, text="选择", command=self.select_input_path).pack(side=tk.RIGHT)
        
        # 输出路径选择部分
        output_frame = ttk.LabelFrame(main_frame, text="选择输出路径（可选）")
        output_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        output_path_frame = ttk.Frame(output_frame)
        output_path_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        self.output_entry = ttk.Entry(output_path_frame, width=50)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(output_path_frame, text="选择", command=self.select_output_path).pack(side=tk.RIGHT)
        
        # 压缩质量选择部分
        quality_frame = ttk.LabelFrame(main_frame, text="选择压缩质量 (0 - 100)")
        quality_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        
        quality_slider_frame = ttk.Frame(quality_frame)
        quality_slider_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        quality_scale = ttk.Scale(quality_slider_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                 variable=self.quality, command=self.debounced_update_estimated_size)
        quality_scale.set(15)  # 降低默认质量
        quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.quality_label = ttk.Label(quality_slider_frame, text=f"当前质量: {self.quality.get()}")
        self.quality_label.pack(side=tk.RIGHT)
        
        # 目标文件大小选择部分
        size_frame = ttk.LabelFrame(main_frame, text="目标文件大小 (可选)")
        size_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        
        size_input_frame = ttk.Frame(size_frame)
        size_input_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        self.size_entry = ttk.Entry(size_input_frame, width=15)
        self.size_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.size_unit = ttk.Combobox(size_input_frame, values=["KB", "MB"], width=5, state="readonly")
        self.size_unit.current(0)
        self.size_unit.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(size_input_frame, text="应用", command=self.apply_target_size).pack(side=tk.LEFT)
        
        # 显示预估大小的标签
        self.size_label = ttk.Label(main_frame, text="请选择文件或文件夹", anchor=tk.W)
        self.size_label.grid(row=5, column=0, sticky="ew", padx=5, pady=5)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=6, column=0, sticky="ew", padx=5, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="进度:", anchor=tk.W)
        self.progress_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 高级选项部分
        advanced_frame = ttk.LabelFrame(main_frame, text="高级压缩选项")
        advanced_frame.grid(row=7, column=0, sticky="ew", padx=5, pady=5)
        
        # 分辨率选项
        resize_frame = ttk.Frame(advanced_frame)
        resize_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        ttk.Label(resize_frame, text="缩放比例:").pack(side=tk.LEFT)
        self.resize_scale = ttk.Scale(resize_frame, from_=10, to=100, orient=tk.HORIZONTAL)
        self.resize_scale.set(80)  # 默认降低分辨率
        self.resize_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.resize_label = ttk.Label(resize_frame, text="80%")
        self.resize_label.pack(side=tk.LEFT)
        
        # 颜色选项
        color_frame = ttk.Frame(advanced_frame)
        color_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        self.grayscale = tk.BooleanVar(value=False)
        ttk.Checkbutton(color_frame, text="部分灰度处理", variable=self.grayscale).pack(side=tk.LEFT)
        
        self.reduce_colors = tk.BooleanVar(value=False)
        ttk.Checkbutton(color_frame, text="减少颜色数量", variable=self.reduce_colors).pack(side=tk.LEFT, padx=(10,0))
        
        # 极限压缩选项
        self.extreme_checkbox = ttk.Checkbutton(
            advanced_frame, text="极限压缩（可能影响质量）", variable=self.extreme_compression,
            command=self.update_ui_state)
        self.extreme_checkbox.pack(side=tk.LEFT, padx=(10,0), pady=5)
        
        # 开始压缩按钮
        self.compress_button = ttk.Button(main_frame, text="开始压缩", command=self.start_compression)
        self.compress_button.grid(row=8, column=0, sticky="ew", padx=5, pady=10)
        
        # 设置列权重，使其可扩展
        main_frame.columnconfigure(0, weight=1)
        
        # 绑定缩放比例更新事件
        self.resize_scale.config(command=self.update_resize_label)
        
    def update_resize_label(self, value):
        """更新缩放比例标签"""
        self.resize_label.config(text=f"{int(float(value))}%")
        
    def update_ui(self):
        """
        更新界面状态
        """
        self.input_entry.delete(0, tk.END)
        self.output_entry.delete(0, tk.END)
        self.size_label.config(text="请选择文件或文件夹")
        self.progress["value"] = 0
        self.selected_path = ""
        self.output_path = ""
        self.update_ui_state()
        
    def update_ui_state(self):
        """
        根据极限压缩选项更新UI状态
        """
        if self.extreme_compression.get():
            # 禁用部分选项，使用极限压缩设置
            self.quality.set(10)
            self.resize_scale.set(70)
            self.quality_label.config(text="极限质量: 10")
            self.resize_label.config(text="70%")
            self.quality_label.config(foreground="red")
            self.resize_label.config(foreground="red")
        else:
            # 恢复正常设置
            self.quality_label.config(foreground="black")
            self.resize_label.config(foreground="black")
        
    def select_input_path(self):
        """
        选择输入文件或文件夹路径
        """
        if self.is_compressing:
            messagebox.showinfo("提示", "正在压缩中，请等待当前任务完成")
            return
            
        if self.mode.get() == "file":
            path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.gif")])
        else:
            path = filedialog.askdirectory()
            
        if path:
            self.selected_path = path
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, path)
            self.debounced_update_estimated_size()
            
    def select_output_path(self):
        """
        选择输出文件夹路径
        """
        if self.is_compressing:
            messagebox.showinfo("提示", "正在压缩中，请等待当前任务完成")
            return
            
        path = filedialog.askdirectory()
        if path:
            self.output_path = path
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)
            
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
            
        # 获取高级选项
        resize_scale = self.resize_scale.get()
        grayscale = self.grayscale.get()
        reduce_colors = self.reduce_colors.get()
        extreme = self.extreme_compression.get()
            
        if self.mode.get() == "file":
            size = estimate_file_size(
                self.selected_path, quality,
                resize_scale=resize_scale,
                grayscale=grayscale,
                reduce_colors=reduce_colors,
                extreme=extreme
            )
            if size > 0:
                self.size_label.config(text=f"预估压缩后文件大小: {format_size(size)}")
            else:
                self.size_label.config(text="无法预估文件大小，请检查文件格式")
        else:
            self.size_label.config(text="正在预估文件夹内文件大小...")
            
            threading.Thread(
                target=estimate_folder_size,
                args=(
                    self.selected_path, 
                    quality, 
                    self.output_queue,
                    resize_scale,
                    grayscale,
                    reduce_colors,
                    extreme
                ),
                daemon=True
            ).start()
            self.master.after(100, self.check_estimate_result)
            
    def check_estimate_result(self):
        """
        检查异步预估结果
        """
        if not self.output_queue.empty():
            total_size = self.output_queue.get()
            if total_size > 0:
                self.size_label.config(text=f"预估所有压缩后文件总大小: {format_size(total_size)}")
            else:
                self.size_label.config(text="无法预估文件夹大小，请检查文件格式")
        else:
            self.master.after(100, self.check_estimate_result)
            
    def compress_to_target_size(self, input_path, output_path, target_bytes, max_iterations=10, tolerance=0.05,
                              resize_scale=100, grayscale=False, reduce_colors=False, extreme=False):
        """
        精确压缩到目标文件大小，使用二分查找算法，增强压缩效果
        """
        original_size = os.path.getsize(input_path)
        if original_size <= target_bytes:
            return original_size, 100
            
        low = 5
        high = 100
        best_quality = 80
        best_size = original_size
        
        for i in range(max_iterations):
            quality = (low + high) // 2
            # 增加收敛条件，如果high和low非常接近，提前结束
            if high - low <= 5:
                break
                
            # 创建临时文件估算大小
            temp_file = generate_temp_file_path(input_path)
            try:
                result = compress_image(input_path, temp_file, quality, 
                                     resize_scale=resize_scale, 
                                     grayscale=grayscale, 
                                     reduce_colors=reduce_colors,
                                     extreme=extreme)
                if isinstance(result, tuple):
                    temp_size = result[0]
                    if temp_size == 0:
                        # 压缩失败，尝试其他参数
                        high = quality - 1
                        continue
                else:
                    temp_size = result
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            if abs(temp_size - target_bytes) / target_bytes <= tolerance:
                best_quality = quality
                best_size = temp_size
                break
                
            if temp_size > target_bytes:
                high = quality - 1
            else:
                low = quality + 1
                
            if abs(temp_size - target_bytes) < abs(best_size - target_bytes):
                best_quality = quality
                best_size = temp_size
                
        # 执行实际压缩
        actual_size = compress_image(input_path, output_path, best_quality,
                                  resize_scale=resize_scale,
                                  grayscale=grayscale,
                                  reduce_colors=reduce_colors,
                                  extreme=extreme)
        if isinstance(actual_size, tuple):
            actual_size = actual_size[0]
        return actual_size, best_quality
        
    def apply_target_size(self):
        """
        应用用户指定的目标文件大小
        """
        try:
            # 验证输入
            target_size_str = self.size_entry.get().strip()
            if not target_size_str:
                return
                
            try:
                target_size = float(target_size_str)
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
                return
                
            if target_size <= 0:
                messagebox.showerror("错误", "目标大小必须大于0")
                return
                
            # 转换为字节
            unit = self.size_unit.get()
            if unit == "KB":
                target_bytes = target_size * 1024
            else:  # MB
                target_bytes = target_size * 1024 * 1024
                
            # 获取原始大小
            if not self.selected_path:
                messagebox.showerror("错误", "请先选择文件或文件夹")
                return
                
            if self.mode.get() == "file":
                original_size = os.path.getsize(self.selected_path)
                if original_size <= target_bytes:
                    messagebox.showinfo("提示", "目标大小大于或等于原始文件大小，无需压缩")
                    return
                    
                # 获取高级选项
                resize_scale = self.resize_scale.get()
                grayscale = self.grayscale.get()
                reduce_colors = self.reduce_colors.get()
                extreme = self.extreme_compression.get()
                
                # 使用临时文件测试压缩
                temp_file = generate_temp_file_path(self.selected_path)
                result = self.compress_to_target_size(
                    self.selected_path, temp_file, target_bytes,
                    resize_scale=resize_scale, grayscale=grayscale, 
                    reduce_colors=reduce_colors, extreme=extreme)
                os.remove(temp_file)
                
                if isinstance(result, tuple):
                    actual_size, quality = result
                    # 更新质量设置
                    self.quality.set(quality)
                    self.quality_label.config(text=f"精确质量: {quality}")
                    self.size_label.config(text=f"预估压缩后大小: {format_size(actual_size)}")
                else:
                    messagebox.showerror("错误", "无法达到目标大小")
            else:
                messagebox.showinfo("提示", "文件夹模式暂不支持目标大小设置")
                
        except Exception as e:
            messagebox.showerror("错误", f"设置目标大小时出错: {str(e)}")
            
    def start_compression(self):
        """
        开始压缩任务
        """
        if self.is_compressing:
            messagebox.showinfo("提示", "正在压缩中，请等待当前任务完成")
            return
            
        quality = self.quality.get()
        if not self.selected_path:
            messagebox.showerror("错误", "请选择输入文件或文件夹")
            return
            
        self.is_compressing = True
        self.compress_button.config(state=tk.DISABLED)
        self.progress["value"] = 0
        
        # 确认对话框，特别是在极限压缩模式下
        extreme = self.extreme_compression.get()
        if extreme:
            confirm = messagebox.askyesno("确认", "极限压缩模式可能会显著影响图片质量，是否继续？")
            if not confirm:
                self.is_compressing = False
                self.compress_button.config(state=tk.NORMAL)
                return
                
        if self.mode.get() == "file":
            self.executor.submit(self.compress_single_file, quality)
        else:
            self.executor.submit(self.compress_folder, quality)
            
    def compress_single_file(self, quality):
        """压缩单个文件的处理函数"""
        try:
            # 使用自定义输出路径或默认路径
            if self.output_path and os.path.isdir(self.output_path):
                output_dir = self.output_path
                file_name = os.path.basename(self.selected_path)
                output_file = os.path.join(output_dir, f"compressed_{file_name}")
            else:
                output_dir = os.path.dirname(self.selected_path)
                file_name = os.path.basename(self.selected_path)
                output_file = os.path.join(output_dir, f"compressed_{file_name}")
                if not self.output_path:  # 如果输出路径为空
                    self.master.after(0, lambda: messagebox.showinfo("提示", "未选择输出路径，将使用输入文件所在目录"))
            
            # 获取高级选项
            resize_scale = self.resize_scale.get()
            grayscale = self.grayscale.get()
            reduce_colors = self.reduce_colors.get()
            extreme = self.extreme_compression.get()
            
            # 检查是否设置了目标大小
            target_size_str = self.size_entry.get().strip()
            if target_size_str:
                try:
                    target_size = float(target_size_str)
                    unit = self.size_unit.get()
                    target_bytes = target_size * 1024 if unit == "KB" else target_size * 1024 * 1024
                    
                    # 压缩到目标大小
                    result = self.compress_to_target_size(
                        self.selected_path, output_file, target_bytes,
                        resize_scale=resize_scale, grayscale=grayscale, 
                        reduce_colors=reduce_colors, extreme=extreme)
                    
                    # 统一处理返回结果
                    if isinstance(result, tuple):
                        compressed_size, used_quality = result
                        if compressed_size == 0:
                            error = result[1] if len(result) > 1 else "未知错误"
                            self.master.after(0, lambda: messagebox.showerror("错误", f"压缩失败: {error}"))
                            return
                    else:
                        compressed_size = result
                except ValueError:
                    # 目标大小格式错误，使用默认质量压缩
                    result = compress_image(
                        self.selected_path, output_file, quality,
                        resize_scale=resize_scale, grayscale=grayscale, 
                        reduce_colors=reduce_colors, extreme=extreme)
                    
                    # 处理压缩结果
                    if isinstance(result, tuple):
                        compressed_size, error = result
                        if compressed_size == 0:
                            self.master.after(0, lambda: messagebox.showerror("错误", f"压缩失败: {error}"))
                            return
                    else:
                        compressed_size = result
            else:
                # 没有设置目标大小，使用默认质量压缩
                result = compress_image(
                    self.selected_path, output_file, quality,
                    resize_scale=resize_scale, grayscale=grayscale, 
                    reduce_colors=reduce_colors, extreme=extreme)
                
                # 处理压缩结果
                if isinstance(result, tuple):
                    compressed_size, error = result
                    if compressed_size == 0:
                        self.master.after(0, lambda: messagebox.showerror("错误", f"压缩失败: {error}"))
                        return
                else:
                    compressed_size = result
            
            # 压缩成功处理
            original_size = os.path.getsize(self.selected_path)
            reduction = 100 - int((compressed_size / original_size) * 100)
            self.master.after(0, lambda: messagebox.showinfo(
                "成功", 
                f"压缩完成!\n\n"
                f"原始大小: {original_size//1024} KB\n"
                f"压缩后大小: {compressed_size//1024} KB\n"
                f"缩减比例: {reduction}%"
            ))
            
            # 重置压缩状态
            self.is_compressing = False
            self.compress_button.config(state=tk.NORMAL)
            self.progress["value"] = 100
            
        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("错误", f"压缩过程中发生意外错误: {str(e)}"))
            self.is_compressing = False
            self.compress_button.config(state=tk.NORMAL)