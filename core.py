from PIL import Image
import os
import threading
import time
from queue import Queue
import functools

def compress_image(input_path, output_path, quality=80, resize_scale=100, 
                  grayscale=False, reduce_colors=False, extreme=False):
    """
    压缩单个图片文件，增强压缩效果，改进格式处理
    """
    try:
        with Image.open(input_path) as img:
            # 确定输出格式
            output_format = 'JPEG'
            if input_path.lower().endswith(('.png', '.gif')) or img.mode in ('RGBA', 'LA') or (reduce_colors and extreme):
                output_format = 'PNG'
            
            save_kwargs = {'optimize': True}
            
            # 极限压缩选项
            if extreme:
                resize_scale = min(resize_scale, 70)  # 最大70%缩放
                quality = max(quality, 10)  # 最低质量10
                
                if not reduce_colors and output_format == 'PNG':
                    # 强制减少颜色
                    img = img.convert('P', palette=Image.ADAPTIVE, colors=64)
                    save_kwargs = {'optimize': True}
                else:
                    save_kwargs['quality'] = quality
            else:
                save_kwargs['quality'] = quality
            
            # 处理透明图片
            if img.mode in ('RGBA', 'LA'):
                if output_format == 'JPEG':
                    # 转换为RGB，白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGBA')
            elif img.mode == 'P' and 'transparency' in img.info:
                img = img.convert('RGBA' if output_format == 'PNG' else 'RGB')
            
            # 应用缩放
            if resize_scale < 100:
                new_width = int(img.width * resize_scale / 100)
                new_height = int(img.height * resize_scale / 100)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 应用灰度处理
            if grayscale:
                if img.mode != 'L':
                    width, height = img.size
                    top_half = img.crop((0, 0, width, height//2))
                    bottom_half = img.crop((0, height//2, width, height))
                    bottom_half = bottom_half.convert('L')
                    img = Image.new('RGB', (width, height))
                    img.paste(top_half, (0, 0))
                    img.paste(bottom_half, (0, height//2))
            
            # 减少颜色数量
            if reduce_colors and img.mode in ('RGB', 'RGBA'):
                colors = 32 if extreme else 64
                img = img.convert('P', palette=Image.ADAPTIVE, colors=colors)
                output_format = 'PNG'
                save_kwargs = {'optimize': True}
            
            # 针对PNG的特殊处理
            if output_format == 'PNG':
                if 'quality' in save_kwargs:
                    del save_kwargs['quality']
                save_kwargs['compress_level'] = 9  # 最高压缩级别
            
            # 保存图片
            img.save(output_path, format=output_format, **save_kwargs)
            
            return os.path.getsize(output_path)
    except Exception as e:
        print(f"处理 {input_path} 时出错: {e}")
        # 这里不直接显示错误，而是返回错误信息
        return 0, str(e)

def estimate_file_size(file_path, quality, resize_scale=100, grayscale=False, reduce_colors=False, extreme=False):
    """
    预估单个文件压缩后的大小，考虑高级选项，改进格式处理
    """
    try:
        with Image.open(file_path) as img:
            # 确定输出格式
            output_format = 'JPEG'
            if file_path.lower().endswith(('.png', '.gif')) or img.mode in ('RGBA', 'LA') or (reduce_colors and extreme):
                output_format = 'PNG'
            
            temp_output = generate_temp_file_path(file_path)
            save_kwargs = {'optimize': True}
            
            # 极限压缩选项
            if extreme:
                resize_scale = min(resize_scale, 70)
                quality = max(quality, 10)
                
                if not reduce_colors and output_format == 'PNG':
                    img = img.convert('P', palette=Image.ADAPTIVE, colors=64)
                    save_kwargs = {'optimize': True}
                else:
                    save_kwargs['quality'] = quality
            else:
                save_kwargs['quality'] = quality
            
            # 应用缩放
            if resize_scale < 100:
                new_width = int(img.width * resize_scale / 100)
                new_height = int(img.height * resize_scale / 100)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 应用灰度处理
            if grayscale:
                if img.mode != 'L':
                    width, height = img.size
                    top_half = img.crop((0, 0, width, height//2))
                    bottom_half = img.crop((0, height//2, width, height))
                    bottom_half = bottom_half.convert('L')
                    img = Image.new('RGB', (width, height))
                    img.paste(top_half, (0, 0))
                    img.paste(bottom_half, (0, height//2))
            
            # 减少颜色数量
            if reduce_colors and img.mode in ('RGB', 'RGBA'):
                colors = 32 if extreme else 64
                img = img.convert('P', palette=Image.ADAPTIVE, colors=colors)
                output_format = 'PNG'
                save_kwargs = {'optimize': True}
            
            # 针对PNG的特殊处理
            if output_format == 'PNG':
                if 'quality' in save_kwargs:
                    del save_kwargs['quality']
                save_kwargs['compress_level'] = 9
            
            img.save(temp_output, format=output_format, **save_kwargs)
            size = os.path.getsize(temp_output)
            os.remove(temp_output)
            return size
    except Exception as e:
        print(f"预估 {file_path} 大小时出错: {e}")
        # 这里返回0表示预估失败
        return 0

def estimate_folder_size(folder_path, quality, output_queue, resize_scale=100, grayscale=False, reduce_colors=False, extreme=False):
    """
    异步预估文件夹内所有图片文件压缩后的总大小，考虑高级选项
    """
    total_size = 0
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    file_path = os.path.join(root, file)
                    size = estimate_file_size(
                        file_path, quality,
                        resize_scale=resize_scale,
                        grayscale=grayscale,
                        reduce_colors=reduce_colors,
                        extreme=extreme
                    )
                    total_size += size
    except Exception as e:
        print(f"预估文件夹 {folder_path} 大小时出错: {e}")
    output_queue.put(total_size)

def generate_temp_file_path(original_path):
    """根据原始文件扩展名生成临时文件路径"""
    temp_timestamp = str(int(time.time() * 1000))
    ext = os.path.splitext(original_path)[1]
    return f"temp_compressed_{temp_timestamp}{ext}"

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