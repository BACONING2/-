import ctypes
import time

import pyautogui

from config import CLICK_DELAY


user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_MOVE = 0x0001


def _win32_click(target_x, target_y, duration=CLICK_DELAY):
    """用 Win32 API 模拟鼠标事件，支持后台/非前台窗口点击。"""
    if duration > 0:
        time.sleep(min(duration, 0.05))

    user32.SetCursorPos(int(target_x), int(target_y))
    time.sleep(max(0.01, min(duration, 0.03)))
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def drag_position(start_x, start_y, end_x, end_y, duration=0.25):
    """从一个点拖到另一个点，适合列表滚动/拖动界面。"""
    user32.SetCursorPos(int(start_x), int(start_y))
    time.sleep(0.02)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    steps = max(8, int(max(abs(end_x - start_x), abs(end_y - start_y)) / 5))
    for i in range(1, steps + 1):
        progress = i / steps
        x = int(start_x + (end_x - start_x) * progress)
        y = int(start_y + (end_y - start_y) * progress)
        user32.SetCursorPos(x, y)
        time.sleep(max(0.005, duration / steps))
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def click_position(x, y, offset=(0, 0), duration=CLICK_DELAY):
    """点击屏幕上某个坐标，可带偏移。"""
    target_x = x + offset[0]
    target_y = y + offset[1]
    try:
        _win32_click(target_x, target_y, duration=duration)
    except Exception:
        pyautogui.moveTo(target_x, target_y, duration=duration)
        pyautogui.click(target_x, target_y)


def click_global_position(x, y, offset=(0, 0), duration=CLICK_DELAY):
    """点击屏幕全局坐标，适合后台/窗口模式。"""
    target_x = x + offset[0]
    target_y = y + offset[1]
    try:
        _win32_click(target_x, target_y, duration=duration)
    except Exception:
        pyautogui.click(target_x, target_y, duration=duration)
