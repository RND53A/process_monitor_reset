"""
图标缓存模块
从可执行文件提取图标，使用 LRU 缓存限制内存占用
"""
import os
import win32gui
import win32ui
from PIL import Image, ImageTk
from collections import OrderedDict

class IconCache:
    def __init__(self, maxsize=200):
        self.cache = OrderedDict()
        self.maxsize = maxsize

    def get_icon(self, exe_path, size=(16, 16)):
        """获取图标 PhotoImage 对象，若缓存已满则删除最旧的"""
        if not exe_path or not os.path.exists(exe_path):
            return None
        key = (exe_path, size)
        if key in self.cache:
            # 移动到末尾表示最近使用
            self.cache.move_to_end(key)
            return self.cache[key]

        try:
            large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0, 1)
            if large_icons and large_icons[0]:
                hicon = large_icons[0]
                dc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                memdc = dc.CreateCompatibleDC()
                bmp = win32ui.CreateBitmap()
                bmp.CreateCompatibleBitmap(dc, size[0], size[1])
                memdc.SelectObject(bmp)
                win32gui.DrawIconEx(memdc.GetHandleOutput(), 0, 0, hicon, size[0], size[1], 0, 0, 3)
                bmpinfo = bmp.GetInfo()
                bmpbits = bmp.GetBitmapBits(True)
                img = Image.frombuffer('RGBA', (size[0], size[1]), bmpbits, 'raw', 'BGRA', 0, 1)
                photo = ImageTk.PhotoImage(img)
                # 限制缓存大小
                if len(self.cache) >= self.maxsize:
                    self.cache.popitem(last=False)
                self.cache[key] = photo
                win32gui.DestroyIcon(hicon)
                bmp.DeleteObject()
                memdc.DeleteDC()
                dc.DeleteDC()
                return photo
        except Exception as e:
            pass
        return None
