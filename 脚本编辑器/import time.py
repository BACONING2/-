"""Legacy duplicate prototype.

This file is intentionally left as a harmless stub so it does not run or clash
with the actual project runtime. The valid implementation lives in [main.py](main.py)
and the editor is in [gui.py](gui.py).
"""

# Intentionally blank; no stale automation logic is executed from here.


templates = load_templates(ICON_DIR)


def capture_screen():
    """截取屏幕当前帧。"""
    screenshot = sct.grab(monitor)
    frame = np.array(screenshot)
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def match_all_templates(screen_img, templates, threshold, use_multi_scale, scale_range, scale_step):
    """对所有模板做匹配，返回 {模板名: ((x, y), confidence)}。"""
    screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
    results = {}

    for name, tpl in templates.items():
        tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
        best_val = -1.0
        best_loc = None
        best_size = tpl_gray.shape[::-1]

        if use_multi_scale:
            for scale in np.arange(scale_range[0], scale_range[1] + scale_step, scale_step):
                resized = cv2.resize(tpl_gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                rh, rw = resized.shape
                if rh > screen_gray.shape[0] or rw > screen_gray.shape[1]:
                    continue
                result = cv2.matchTemplate(screen_gray, resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                if max_val > best_val:
                    best_val = max_val
                    best_loc = max_loc
                    best_size = (rw, rh)
        else:
            result = cv2.matchTemplate(screen_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
            _, best_val, _, best_loc = cv2.minMaxLoc(result)
            best_size = tpl_gray.shape[::-1]

        if best_val >= threshold and best_loc is not None:
            center_x = best_loc[0] + best_size[0] // 2
            center_y = best_loc[1] + best_size[1] // 2
            results[name] = ((center_x, center_y), float(best_val))
        else:
            results[name] = (None, float(best_val))

    return results


def click_position(x, y, offset=(0, 0), duration=CLICK_DELAY):
    """坐标点击，支持偏移。"""
    target_x = x + offset[0]
    target_y = y + offset[1]
    pyautogui.moveTo(target_x, target_y, duration=duration)
    pyautogui.click(target_x, target_y)


def wait_until_template_disappears(template_name, timeout=10.0, poll_interval=0.1):
    """等待指定模板消失，返回 True 表示消失，False 表示超时。"""
    start = time.time()
    while True:
        screen_img = capture_screen()
        results = match_all_templates(screen_img, templates, THRESHOLD, USE_MULTI_SCALE, SCALE_RANGE, SCALE_STEP)
        center, conf = results.get(template_name, (None, -1.0))
        if center is None:
            return True

        if timeout > 0 and (time.time() - start) > timeout:
            return False
        time.sleep(poll_interval)


def wait_until_template_appears(template_name, timeout=10.0, poll_interval=0.1):
    """等待指定模板出现，返回位置和置信度，超时返回 (None, None)。"""
    start = time.time()
    while True:
        screen_img = capture_screen()
        results = match_all_templates(screen_img, templates, THRESHOLD, USE_MULTI_SCALE, SCALE_RANGE, SCALE_STEP)
        center, conf = results.get(template_name, (None, -1.0))
        if center is not None:
            return center, conf

        if timeout > 0 and (time.time() - start) > timeout:
            return None, None
        time.sleep(poll_interval)


def show_complete_message():
    """弹出完成提示。"""
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("脚本执行完成", "所有步骤已完成，脚本已停止运行。")
    root.destroy()


# ==================== 任务定义 ====================
# 任务说明：
# - template: 需要识别的模板名
# - timeout: 等待模板出现的超时时间（秒）
# - click: 是否点击
# - offset: 点击偏移 (dx, dy)
# - after_wait: 点击后固定等待时间（秒）
# - wait_for: 任务完成后的等待方式，可选：
#      "disappear" -> 等待当前图标消失
#      "time"      -> 等固定时间
#      "next_appear" -> 等待下一步图标出现
# - next_template: 当 wait_for="next_appear" 时，等待的下一步图标
# - required: 是否必须出现
# - description: 日志说明
TASKS = [
    {
        "template": "start_button",
        "timeout": 10,
        "click": True,
        "offset": (0, 0),
        "after_wait": 0.5,
        "wait_for": "disappear",
        "required": True,
        "description": "点击开始按钮并等待战斗开始"
    },
    {
        "template": "attack_button",
        "timeout": 10,
        "click": True,
        "offset": (0, 0),
        "after_wait": 1.0,
        "wait_for": "disappear",
        "required": True,
        "description": "点击攻击按钮并等待动作结束"
    },
    {
        "template": "reward_button",
        "timeout": 8,
        "click": True,
        "offset": (0, 0),
        "after_wait": 0.5,
        "wait_for": "time",
        "required": False,
        "description": "领取奖励（如果出现）"
    },
    {
        "template": "next_button",
        "timeout": 8,
        "click": True,
        "offset": (0, 0),
        "after_wait": 0.5,
        "wait_for": "disappear",
        "required": True,
        "description": "点击下一步继续"
    },
]


# ==================== 主逻辑：状态机 ====================
def execute_task(task):
    """执行单个任务：识别 → 点击 → 等待处理结果 → 继续。"""
    tpl_name = task["template"]
    timeout = task.get("timeout", 10)
    required = task.get("required", True)
    description = task.get("description", tpl_name)

    print(f"\n>>> 任务: {description}")
    start_time = time.time()

    while True:
        screen_img = capture_screen()
        results = match_all_templates(screen_img, templates, THRESHOLD, USE_MULTI_SCALE, SCALE_RANGE, SCALE_STEP)
        center, conf = results.get(tpl_name, (None, -1.0))

        if center is not None:
            print(f"  识别到 '{tpl_name}'，置信度: {conf:.2f}，坐标: {center}")
            if task.get("click", True):
                offset = task.get("offset", (0, 0))
                click_position(center[0], center[1], offset)
                print(f"  已点击坐标: ({center[0] + offset[0]}, {center[1] + offset[1]})")

            wait_mode = task.get("wait_for", "time")
            if wait_mode == "disappear":
                wait_result = wait_until_template_disappears(tpl_name, timeout=task.get("wait_timeout", 12))
                if not wait_result:
                    print(f"  等待 '{tpl_name}' 消失超时，继续下一步。")
                else:
                    print(f"  '{tpl_name}' 已消失，进入下一步。")
            elif wait_mode == "next_appear":
                next_tpl = task.get("next_template")
                if not next_tpl:
                    raise ValueError(f"任务 '{tpl_name}' 配置了 wait_for='next_appear'，但未提供 next_template。")
                next_center, next_conf = wait_until_template_appears(next_tpl, timeout=task.get("wait_timeout", 12))
                if next_center is None:
                    print(f"  等待 '{next_tpl}' 出现超时。")
                else:
                    print(f"  检测到下一步 UI '{next_tpl}'，置信度 {next_conf:.2f}，坐标 {next_center}")
            else:
                time.sleep(task.get("after_wait", 0.5))

            return True

        if timeout > 0 and (time.time() - start_time) > timeout:
            print(f"  超时未检测到 '{tpl_name}'")
            if required:
                raise RuntimeError(f"必需步骤 '{tpl_name}' 未在超时时间内出现，脚本停止。")
            print(f"  该步骤为可选步骤，跳过。")
            return False

        time.sleep(0.1)


def run_task_queue(tasks, loop=False):
    """按顺序执行任务队列，可循环。"""
    print("开始执行自动脚本，按 Ctrl+C 手动停止")
    try:
        while True:
            for task in tasks:
                try:
                    execute_task(task)
                except RuntimeError as e:
                    print(f"错误: {e}")
                    show_complete_message()
                    return

            print("\n任务队列执行完毕。")
            if not loop:
                show_complete_message()
                return
            print("任务队列将重新开始循环...")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n用户手动停止脚本。")

    finally:
        if SHOW_PREVIEW:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    # 这个脚本会在识别到模板后点击，然后等待本次动作结束，再进入下一步。
    # 如果需要循环执行，可将 loop 改为 True。
    run_task_queue(TASKS, loop=False)
