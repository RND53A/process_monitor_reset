"""
蓝屏模拟程序
显示全屏蓝屏错误界面，按ESC退出，支持自定义文字内容和字体大小
"""
import tkinter as tk
import json
import sys
import os
import random
import string

def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和 PyInstaller 打包"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def quit_fullscreen(event=None):
    """按下 Esc 键时退出全屏并关闭程序"""
    root.destroy()

def load_config(filename):
    """从 JSON 文件加载配置，若文件不存在则返回默认配置"""
    default_config = {
        "font_size": 30,
        "lines": [
            {"text": "  :("},
            {"text": "            你的电脑遇到问题，需要重新启动。"},
            {"text": "            我们只收集某些错误信息，然后为你重新启动。"},
            {"text": ""},
            {"text": "            0%完成"},
            {"text": ""},
            {"text": "                                                     有关此问题的详细信息和可能的解决方案，请访问 https://www.windows.com/stopcode"},
            {"text": ""},
            {"text": "                                                     如果致电支持人员，请向他们提供以下信息："},
            {"text": "                                                     终止代码：CRITICAL_PROCESS_DIED"},
            {"text": ""}
        ]
    }

    # 使用 resource_path 获取正确路径（开发环境当前目录，打包后内部临时目录）
    try:
        config_path = resource_path(filename)
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if "font_size" not in config:
            config["font_size"] = default_config["font_size"]
        if "lines" not in config:
            config["lines"] = default_config["lines"]
        return config
    except Exception as e:
        print(f"读取配置文件失败，使用默认配置。错误信息：{e}")
        return default_config

# 加载配置（文件名使用相对路径，resource_path会自动处理）
config = load_config("bluescreen.json")

root = tk.Tk()
root.title("bluescreen")
root.attributes('-fullscreen', True)
root.configure(bg='#0F4C81')
root.config(cursor="none")
root.wm_attributes('-topmost', True)

screen_width = root.winfo_screenwidth()
wrap_width = int(screen_width * 0.8)

container = tk.Frame(root, bg='#0F4C81')
container.pack(anchor='nw', padx=50, pady=150)

global_font_size = config.get("font_size", 20)

# 显示文字行
for line_config in config["lines"]:
    text = line_config.get("text", "")
    font_size = line_config.get("font_size", global_font_size)
    font = ('Microsoft YaHei', font_size)

    label = tk.Label(
        container,
        text=text,
        fg='white',
        bg='#0F4C81',
        font=font,
        wraplength=wrap_width,
        justify=tk.LEFT,
        anchor='w'
    )
    label.pack(anchor='w', pady=2)

# 生成随机二维码（位置硬编码，按用户要求不修改5.5）
try:
    import qrcode
    from PIL import Image, ImageTk

    random_content = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=3,
    )
    qr.add_data(random_content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0F4C81", back_color="white")
    qr_image = ImageTk.PhotoImage(img)

    qr_label = tk.Label(root, image=qr_image, bg='#0F4C81')
    qr_label.image = qr_image

    x = screen_width - img.width - 1722
    y = root.winfo_screenheight() - img.height - 258
    qr_label.place(x=x, y=y)

except ImportError:
    print("未安装 qrcode 或 PIL，无法生成二维码。请运行：pip install qrcode[pil]")

root.bind('<Escape>', quit_fullscreen)
root.focus_force()
root.mainloop()