import ctypes
from ctypes import wintypes
import re
import obspython as obs

# --- WinAPI 定义 ---
user32 = ctypes.WinDLL('user32', use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
EnumWindows = user32.EnumWindows
EnumWindows.restype = wintypes.BOOL
EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
IsWindowVisible = user32.IsWindowVisible
IsWindowVisible.restype = wintypes.BOOL
IsWindowVisible.argtypes = [wintypes.HWND]
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextLengthW.restype = ctypes.c_int
GetWindowTextLengthW.argtypes = [wintypes.HWND]
GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.restype = ctypes.c_int
GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

# --- 全局变量 ---
enabled = False
interval = 1000
text_source_name = ""
filter_keyword = ""
filter_rule = r'^(.*?)\s*\[foobar2000[^\]]*\]'
prefix = ""
timer_active = False

# --- 窗口标题枚举 ---
def enum_windows():
    titles = []
    @WNDENUMPROC
    def enum_proc(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
                if title:
                    titles.append(title)
        return True
    EnumWindows(enum_proc, 0)
    return titles

def find_window_title_by_keyword(keyword):
    titles = enum_windows()
    for title in titles:
        if keyword.lower() in title.lower():
            return title
    return None

def apply_filter(title, rule):
    if not rule.strip():
        return title
    try:
        match = re.search(rule, title)
        if match:
            return match.group(1)
    except re.error:
        pass
    return title

# --- 主功能 ---
def update_text_source():
    if not enabled or not text_source_name:
        return
    title = find_window_title_by_keyword(filter_keyword)
    filtered_text = apply_filter(title, filter_rule) if title else "(未找到窗口)"
    final_text = prefix + filtered_text
    source = obs.obs_get_source_by_name(text_source_name)
    if source:
        settings = obs.obs_source_get_settings(source)
        obs.obs_data_set_string(settings, "text", final_text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)

def timer_callback():
    update_text_source()

# --- OBS 设置界面 ---
def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_bool(props, "enabled", "启用")
    obs.obs_properties_add_text(props, "text_source", "文本源名称", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "filter_keyword", "标题关键词", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "filter_rule", "过滤规则（正则）", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "prefix", "前缀（可选）", obs.OBS_TEXT_DEFAULT)
    return props

def script_update(settings):
    global enabled, text_source_name, filter_keyword, filter_rule, prefix, timer_active
    enabled = obs.obs_data_get_bool(settings, "enabled")
    text_source_name = obs.obs_data_get_string(settings, "text_source")
    filter_keyword = obs.obs_data_get_string(settings, "filter_keyword")
    filter_rule = obs.obs_data_get_string(settings, "filter_rule") or r'^(.*?)\s*\[foobar2000[^\]]*\]'
    prefix = obs.obs_data_get_string(settings, "prefix") or ""

    if timer_active:
        obs.timer_remove(timer_callback)
        timer_active = False

    if enabled and text_source_name:
        obs.timer_add(timer_callback, interval)
        timer_active = True

def script_unload():
    global timer_active
    if timer_active:
        obs.timer_remove(timer_callback)
        timer_active = False

def script_description():
    return "窗口标题过滤器：自动从窗口标题中过滤内容\n示例规则：^(.*?)\\s*\\[foobar2000[^\\]]*\\]"
