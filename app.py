import customtkinter as ctk
import os
import json
import subprocess
import winreg
import zipfile
import shutil
import stat
from PIL import Image
from tkinter import filedialog, messagebox
import webbrowser
import requests
from io import BytesIO
import threading
from datetime import datetime

# 设置外观模式和颜色主题
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# ========================================================
# 日志系统
# ========================================================
class Logger:
    """全局日志系统"""
    def __init__(self):
        self.logs = []
        self.log_file = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'NoS_Launcher', 'nos_launcher_log.txt')

    def log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        # 同时打印到控制台
        print(log_entry)

    def info(self, message):
        self.log(message, "INFO")

    def warning(self, message):
        self.log(message, "WARNING")

    def error(self, message):
        self.log(message, "ERROR")

    def debug(self, message):
        self.log(message, "DEBUG")

    def user_action(self, message):
        """用户操作日志"""
        self.log(message, "USER_ACTION")

    def export_to_file(self, filepath):
        """导出日志到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("NoS Launcher 日志文件\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                for log_entry in self.logs:
                    f.write(log_entry + "\n")
            return True
        except Exception as e:
            print(f"导出日志失败: {e}")
            return False

    def get_all_logs(self):
        """获取所有日志"""
        return "\n".join(self.logs)

# 全局日志实例
logger = Logger()

class DownloadWindow(ctk.CTkToplevel):
    """下载进度窗口"""
    def __init__(self, parent, title="下载中"):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color="#ffffff")

        # 居中显示
        self.update_idletasks()
        x = int(parent.winfo_x() + (parent.winfo_width()/2) - 250)
        y = int(parent.winfo_y() + (parent.winfo_height()/2) - 200)
        self.geometry(f"500x400+{x}+{y}")

        # 日志区域
        self.log_frame = ctk.CTkFrame(self, fg_color="#f0f0f0", corner_radius=10)
        self.log_frame.pack(fill="both", expand=True, padx=15, pady=(15, 5))

        self.log_textbox = ctk.CTkTextbox(
            self.log_frame, width=450, height=280,
            font=("Consolas", 11), fg_color="#ffffff", text_color="#000000"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # 进度条区域
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=10)

        self.status_label = ctk.CTkLabel(
            self.progress_frame, text="准备下载...",
            font=("Microsoft YaHei", 12), text_color="#333333"
        )
        self.status_label.pack(anchor="w")

        self.progressbar = ctk.CTkProgressBar(
            self.progress_frame, width=450, height=15, corner_radius=7
        )
        self.progressbar.pack(fill="x", pady=5)
        self.progressbar.set(0)

        # 关闭按钮（初始隐藏）
        self.close_button = ctk.CTkButton(
            self, text="关闭", width=100, height=32, corner_radius=8, command=self.destroy
        )
        self.download_complete = False
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.download_complete:
            self.destroy()
        else:
            messagebox.showwarning("提示", "下载正在进行中，请稍候...")

    def log(self, message):
        """添加日志"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def set_progress(self, progress):
        """设置进度"""
        self.progressbar.set(progress)

    def set_status(self, status):
        """设置状态"""
        self.status_label.configure(text=status)

    def show_close_button(self):
        """显示关闭按钮"""
        self.close_button.pack(pady=10)
        self.download_complete = True

class NOSLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 配置窗口
        self.title("NoS Launcher")
        self.geometry("650x650")
        self.minsize(550, 550)
        self.configure(fg_color="#426666")
        self.eval('tk::PlaceWindow . center')

        # 数据存储
        self.game_root_paths = [] # 支持多个游戏根目录
        self.current_versions = [] # 存储元组: (版本名, 路径)
        self.version_types = {} # 存储版本类型: "nos" 或 "vanilla"

        self.app_data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'NoS_Launcher')
        if not os.path.isdir(self.app_data_dir):
            os.makedirs(self.app_data_dir, exist_ok=True)
        self.config_file = os.path.join(self.app_data_dir, "config.json")

        self.current_version = "4.0.0" # 当前启动器版本
        self.last_selected_version = "" # 上次选择的版本（记忆功能）

        # 插件版本记录
        self.addon_versions = {}

        # 按钮显示配置（默认都显示）
        self.button_visibility = {
            "addons": True, # 插件文件夹按钮
            "presets": True  # 预设文件夹按钮
        }

        # 当前页面
        self.current_page = "launch"

        # 创建主容器
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # -------------------------------------------------------
        # 导航按钮栏 (最上方)
        # -------------------------------------------------------
        self.nav_frame = ctk.CTkFrame(master=self, fg_color="#426666", corner_radius=0)
        self.nav_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))
        self.nav_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # 导航按钮 - 居中显示
        self.nav_launch_btn = ctk.CTkButton(
            self.nav_frame, text="启动", width=130, height=36, corner_radius=10,
            font=("Microsoft YaHei", 14, "bold"),
            fg_color="#5a8ab5", hover_color="#4a7a9b",
            command=lambda: self.switch_page("launch")
        )
        self.nav_launch_btn.grid(row=0, column=0, padx=5, pady=5)

        self.nav_download_btn = ctk.CTkButton(
            self.nav_frame, text="下载", width=130, height=36, corner_radius=10,
            font=("Microsoft YaHei", 14, "bold"),
            fg_color="#5a6b7a", hover_color="#4a5b6a",
            command=lambda: self.switch_page("download")
        )
        self.nav_download_btn.grid(row=0, column=1, padx=5, pady=5)

        self.nav_settings_btn = ctk.CTkButton(
            self.nav_frame, text="设置", width=130, height=36, corner_radius=10,
            font=("Microsoft YaHei", 14, "bold"),
            fg_color="#5a6b7a", hover_color="#4a5b6a",
            command=lambda: self.switch_page("settings")
        )
        self.nav_settings_btn.grid(row=0, column=2, padx=5, pady=5)

        # -------------------------------------------------------
        # Logo 区域
        # -------------------------------------------------------
        self.logo_frame = ctk.CTkFrame(master=self, fg_color="#426666", corner_radius=0)
        self.logo_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=5)
        self.logo_frame.grid_columnconfigure(0, weight=1)

        self.load_logo()

        # -------------------------------------------------------
        # 分隔线
        # -------------------------------------------------------
        self.separator = ctk.CTkFrame(master=self, height=2, fg_color="#5a7a8a")
        self.separator.grid(row=2, column=0, sticky="ew", padx=50, pady=10)

        # -------------------------------------------------------
        # 内容区域
        # -------------------------------------------------------
        self.content_frame = ctk.CTkFrame(master=self, corner_radius=15, border_width=0, fg_color="#425466")
        self.content_frame.grid(row=3, column=0, padx=30, pady=(0, 25), sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # 创建各页面
        self.create_launch_page()
        self.create_download_page() # 合并后的下载页面
        self.create_settings_page()

        # 默认显示启动页面
        self.switch_page("launch")

        # 在所有UI元素创建后，再加载配置
        self.load_config()

        # 启动时自动检测更新
        self.after(1500, self.check_update_on_startup)

    def switch_page(self, page_name):
        """切换页面"""
        logger.user_action(f"切换到页面: {page_name}")

        # 隐藏所有页面
        self.launch_page.grid_remove()
        self.download_page.grid_remove()
        self.settings_page.grid_remove()

        # 重置所有导航按钮颜色
        self.nav_launch_btn.configure(fg_color="#5a6b7a")
        self.nav_download_btn.configure(fg_color="#5a6b7a")
        self.nav_settings_btn.configure(fg_color="#5a6b7a")

        # 显示选中的页面并高亮对应按钮
        if page_name == "launch":
            self.launch_page.grid()
            self.nav_launch_btn.configure(fg_color="#5a8ab5")
        elif page_name == "download":
            self.download_page.grid()
            self.nav_download_btn.configure(fg_color="#5a8ab5")
            # 切换到下载页面时加载列表
            self.load_addon_list()
            self.load_game_list()
        elif page_name == "settings":
            self.settings_page.grid()
            self.nav_settings_btn.configure(fg_color="#5a8ab5")

        self.current_page = page_name

    # ========================================================
    # 启动页面
    # ========================================================
    def create_launch_page(self):
        """创建启动页面"""
        self.launch_page = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.launch_page.grid(row=0, column=0, sticky="nsew")
        self.launch_page.grid_columnconfigure(0, weight=1)
        self.launch_page.grid_rowconfigure((0,1,2,3,4,5,6), weight=1)

        # 1. 标题
        self.label_title = ctk.CTkLabel(
            master=self.launch_page, text="欢迎使用 NoS Launcher",
            font=("Microsoft YaHei", 22, "bold"), text_color="#ffffff"
        )
        self.label_title.grid(row=0, column=0, pady=(25, 5))

        # 2. 版本选择区域
        self.version_label = ctk.CTkLabel(
            master=self.launch_page, text="当前游戏版本：",
            font=("Microsoft YaHei", 14), text_color="#ffffff"
        )
        self.version_label.grid(row=1, column=0, pady=(10, 5))

        self.version_combobox = ctk.CTkOptionMenu(
            master=self.launch_page, values=["请先在设置中添加文件夹"],
            width=280, height=38, corner_radius=10,
            font=("Microsoft YaHei", 13), dynamic_resizing=False,
            command=self.on_version_changed
        )
        self.version_combobox.grid(row=2, column=0, pady=(0, 15))

        # 3. 启动按钮
        self.launch_button = ctk.CTkButton(
            master=self.launch_page, text="▶ 启动游戏", width=280, height=48,
            corner_radius=12, font=("Microsoft YaHei", 16, "bold"),
            command=self.launch_game, fg_color="#5a8ab5", hover_color="#4a7a9b"
        )
        self.launch_button.grid(row=3, column=0, pady=12)

        # 4. 打开插件文件夹按钮
        self.addons_button = ctk.CTkButton(
            master=self.launch_page, text="打开插件文件夹", width=280, height=38,
            corner_radius=10, font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5", hover_color="#4a7a9b", command=self.open_addons_folder
        )
        self.addons_button.grid(row=4, column=0, pady=8)
        self.addons_button.grid_remove()

        # 5. 打开预设文件夹按钮
        self.presets_button = ctk.CTkButton(
            master=self.launch_page, text="打开预设文件夹", width=280, height=38,
            corner_radius=10, font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5", hover_color="#4a7a9b", command=self.open_presets_folder
        )
        self.presets_button.grid(row=5, column=0, pady=8)
        self.presets_button.grid_remove()

        # 6. 版本号
        self.version_label_bottom = ctk.CTkLabel(
            master=self.launch_page, text=f"NoS Launcher {self.current_version}",
            font=("Microsoft YaHei", 11), text_color="#aaaaaa"
        )
        self.version_label_bottom.grid(row=6, column=0, pady=(15, 20))

    # ========================================================
    # 下载页面（包含插件市场和下载游戏）
    # ========================================================
    def create_download_page(self):
        """创建下载页面"""
        self.download_page = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.download_page.grid(row=0, column=0, sticky="nsew")
        self.download_page.grid_columnconfigure(0, weight=1)
        self.download_page.grid_rowconfigure(0, weight=1)

        # 使用选项卡
        self.download_tabview = ctk.CTkTabview(
            self.download_page, width=550, height=450, corner_radius=10
        )
        self.download_tabview.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        self.download_tabview.add("插件市场")
        self.download_tabview.add("下载游戏")

        # 设置各标签页
        self.setup_addon_tab()
        self.setup_game_download_tab()

    def setup_addon_tab(self):
        """插件市场标签页"""
        addon_frame = self.download_tabview.tab("插件市场")
        addon_frame.grid_columnconfigure(0, weight=1)
        addon_frame.grid_rowconfigure(1, weight=1)

        # 标题区域
        title_frame = ctk.CTkFrame(addon_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(5, 5), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_frame, text="插件市场",
            font=("Microsoft YaHei", 16, "bold"), text_color="#000000"
        ).grid(row=0, column=0, pady=2)

        # 提示信息
        ctk.CTkLabel(
            title_frame, text="下载链接由绿林Greenwoo和帆船提供",
            font=("Microsoft YaHei", 10), text_color="#aaaaaa"
        ).grid(row=1, column=0, pady=(0, 2))

        # 插件列表容器
        self.addon_list_frame = ctk.CTkScrollableFrame(
            addon_frame, width=500, height=300, corner_radius=10
        )
        self.addon_list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.addon_list_frame.grid_columnconfigure(0, weight=1)

    def setup_game_download_tab(self):
        """下载游戏标签页"""
        game_frame = self.download_tabview.tab("下载游戏")
        game_frame.grid_columnconfigure(0, weight=1)
        game_frame.grid_rowconfigure(1, weight=1)

        # 标题区域
        title_frame = ctk.CTkFrame(game_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(5, 5), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_frame, text="下载游戏",
            font=("Microsoft YaHei", 16, "bold"), text_color="#000000"
        ).grid(row=0, column=0, pady=2)

        # 提示信息
        ctk.CTkLabel(
            title_frame, text="请选择游戏版本",
            font=("Microsoft YaHei", 10), text_color="#aaaaaa"
        ).grid(row=1, column=0, pady=(0, 2))

        # 游戏列表容器
        self.game_list_frame = ctk.CTkScrollableFrame(
            game_frame, width=500, height=300, corner_radius=10
        )
        self.game_list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.game_list_frame.grid_columnconfigure(0, weight=1)

    # ========================================================
    # 设置页面
    # ========================================================
    def create_settings_page(self):
        """创建设置页面"""
        self.settings_page = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.settings_page.grid(row=0, column=0, sticky="nsew")
        self.settings_page.grid_columnconfigure(0, weight=1)
        self.settings_page.grid_rowconfigure(1, weight=1)

        # 使用选项卡
        self.settings_tabview = ctk.CTkTabview(
            self.settings_page, width=550, height=380, corner_radius=10
        )
        self.settings_tabview.grid(row=0, column=0, padx=25, pady=20, sticky="nsew")

        # 按你的要求顺序：路径设置 -> 私服编辑 -> 更新 -> 按钮显示 -> 关于
        self.settings_tabview.add("路径设置")
        self.settings_tabview.add("私服编辑")
        self.settings_tabview.add("更新")
        self.settings_tabview.add("按钮显示")
        self.settings_tabview.add("关于")

        # 设置各标签页
        self.setup_settings_path_tab()
        self.setup_settings_servers_tab()      # 私服编辑
        self.setup_settings_update_tab()
        self.setup_settings_buttons_tab()
        self.setup_settings_about_tab()

    def setup_settings_path_tab(self):
        """路径设置标签页"""
        settings_frame = self.settings_tabview.tab("路径设置")
        settings_frame.grid_columnconfigure(0, weight=1)
        settings_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            settings_frame, text="游戏路径设置",
            font=("Microsoft YaHei", 18, "bold"), text_color="#333333"
        ).grid(row=0, column=0, pady=15)

        # 添加路径区域
        add_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        add_frame.grid(row=1, column=0, pady=10, sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)

        self.path_display = ctk.CTkEntry(
            add_frame, width=320, height=35,
            placeholder_text="请输入或选择游戏根目录", corner_radius=8
        )
        self.path_display.pack(side="left", padx=(20, 5))

        ctk.CTkButton(
            add_frame, text="浏览...", width=70, height=35, corner_radius=8,
            command=self.browse_folder
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            add_frame, text="添加路径", width=80, height=35, corner_radius=8,
            fg_color="#28a745", hover_color="#218838", command=self.add_game_path
        ).pack(side="left", padx=5)

        # 路径列表区域
        self.path_list_frame = ctk.CTkScrollableFrame(
            settings_frame, width=450, height=200, corner_radius=10
        )
        self.path_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.path_list_frame.grid_columnconfigure(0, weight=1)

        # 刷新路径列表
        self.refresh_path_list()

        ctk.CTkLabel(
            settings_frame, text="提示：可添加多个游戏路径，检测到游戏目录会自动显示在启动页面",
            text_color="#aaaaaa", font=("Microsoft YaHei", 10)
        ).grid(row=3, column=0, pady=10)

    # --------------------------------------------------------
    # 私服编辑（设置页第二个 Tab）
    # --------------------------------------------------------
    def setup_settings_servers_tab(self):
        """私服编辑标签页"""
        servers_frame = self.settings_tabview.tab("私服编辑")
        servers_frame.grid_columnconfigure(0, weight=1)
        servers_frame.grid_rowconfigure(1, weight=1)

        # 标题
        ctk.CTkLabel(
            servers_frame, text="私服编辑",
            font=("Microsoft YaHei", 18, "bold"), text_color="#333333"
        ).grid(row=0, column=0, pady=15)

        # 远程私服列表（滚动区域）
        self.servers_list_frame = ctk.CTkScrollableFrame(
            servers_frame, width=500, height=180, corner_radius=10
        )
        self.servers_list_frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        self.servers_list_frame.grid_columnconfigure(0, weight=1)

        # 提示 + 状态
        self.servers_status_label = ctk.CTkLabel(
            servers_frame, text="正在加载远程私服列表...",
            font=("Microsoft YaHei", 11), text_color="#555555"
        )
        self.servers_status_label.grid(row=2, column=0, pady=2)

        # 增加私服按钮（弹窗添加）
        self.manual_add_btn = ctk.CTkButton(
            servers_frame, text="增加私服", width=110, height=32, corner_radius=8,
            font=("Microsoft YaHei", 12),
            fg_color="#5a8ab5", hover_color="#4a7a9b",
            command=self._open_add_server_dialog
        )
        self.manual_add_btn.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="w")

        # 按钮行：刷新 + 应用
        btn_frame = ctk.CTkFrame(servers_frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=10)
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.servers_refresh_btn = ctk.CTkButton(
            btn_frame, text="刷新列表", width=110, height=32, corner_radius=8,
            font=("Microsoft YaHei", 12),
            command=self._load_remote_servers_ui
        )
        self.servers_refresh_btn.grid(row=0, column=0, padx=5)

        self.servers_apply_btn = ctk.CTkButton(
            btn_frame, text="应用", width=110, height=32, corner_radius=8,
            font=("Microsoft YaHei", 12),
            fg_color="#28a745", hover_color="#218838",
            command=self._apply_servers_to_region_info
        )
        self.servers_apply_btn.grid(row=0, column=1, padx=5)

        # 小提示
        ctk.CTkLabel(
            servers_frame,
            text="说明：勾选或手动添加私服后点击[应用]",
            font=("Microsoft YaHei", 10), text_color="#777777", wraplength=480
        ).grid(row=5, column=0, pady=(0, 8))

        # 用来保存远程数据：{显示名称: 地址} 以及 UI 控件
        self.servers_remote_items = {}   # {name: addr}
        self.servers_checkboxes = {}     # {name: CTkCheckBox}

        # 进入设置页时自动加载一次
        self._load_remote_servers_ui()

    # --------------------------------------------------------
    # 私服列表 UI
    # --------------------------------------------------------
    def _load_remote_servers_ui(self):
        """从远程拉取 u.json，并根据当前 regionInfo.json 同步勾选框"""
        for w in self.servers_list_frame.winfo_children():
            w.destroy()
        self.servers_remote_items.clear()
        self.servers_checkboxes.clear()
        self.servers_status_label.configure(text="正在加载远程私服列表...")

        def fetch():
            try:
                r = requests.get("https://auojplay.fanchuanovo.cn/NoS_Launcher/servers/u.json", timeout=10)
                r.raise_for_status()
                data = r.json()
                self.after(0, lambda: self._after_remote_servers_loaded(data))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._show_remote_servers_error(err_msg))

        threading.Thread(target=fetch, daemon=True).start()

    def _after_remote_servers_loaded(self, data):
        """远程列表加载完成后，读取 regionInfo.json 并同步勾选"""
        if not data or not isinstance(data, dict):
            self.servers_status_label.configure(text="远程列表为空或格式错误。")
            return

        self.servers_remote_items.clear()
        for name, addr in data.items():
            if isinstance(addr, str):
                self.servers_remote_items[name] = addr

        existing_names = self._read_existing_region_names()
        manual_names = set()

        for n in list(self.servers_remote_items.keys()):
            if n not in data:
                manual_names.add(n)

        selected_names = set(existing_names) | manual_names
        self._rebuild_servers_checkboxes(selected_names, manual_names)

    def _rebuild_servers_checkboxes(self, selected_names, manual_names):
        """在 UI 中重建全部私服勾选框"""
        for w in self.servers_list_frame.winfo_children():
            w.destroy()
        self.servers_checkboxes.clear()

        row = 0
        for name, addr in self.servers_remote_items.items():
            checked = name in selected_names
            cb = ctk.CTkCheckBox(
                self.servers_list_frame, text=name,
                font=("Microsoft YaHei", 12),
                checkbox_width=20, checkbox_height=20, corner_radius=4
            )
            cb.grid(row=row, column=0, padx=10, pady=3, sticky="w")
            if checked:
                cb.select()
            self.servers_checkboxes[name] = cb
            row += 1

        for name in sorted(manual_names):
            if name in self.servers_checkboxes:
                continue
            cb = ctk.CTkCheckBox(
                self.servers_list_frame, text=f"{name}（手动）",
                font=("Microsoft YaHei", 12),
                checkbox_width=20, checkbox_height=20, corner_radius=4
            )
            cb.grid(row=row, column=0, padx=10, pady=3, sticky="w")
            cb.select()
            self.servers_checkboxes[name] = cb
            row += 1

        self.servers_status_label.configure(
            text=f"已加载 {len(self.servers_remote_items)} 个远程私服 + {len(manual_names)} 个手动私服（已自动勾选已有私服）。"
        )

    def _read_existing_region_names(self):
        """读取 regionInfo.json 中 Regions[].Name，返回集合"""
        userprofile = os.environ.get("USERPROFILE", "")
        region_dir = os.path.join(userprofile, "AppData", "LocalLow", "Innersloth", "Among Us")
        region_file = os.path.join(region_dir, "regionInfo.json")

        if not os.path.isfile(region_file):
            return set()

        try:
            try:
                os.chmod(region_file, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass

            with open(region_file, "r", encoding="utf-8-sig") as f:
                base = json.load(f)

            regions = base.get("Regions")
            if not isinstance(regions, list):
                return set()

            names = set()
            for r in regions:
                n = r.get("Name")
                if isinstance(n, str) and n:
                    names.add(n)
            return names
        except Exception:
            return set()

    def _show_remote_servers_error(self, err_msg):
        for w in self.servers_list_frame.winfo_children():
            w.destroy()
        self.servers_status_label.configure(text=f"加载远程私服列表失败：{err_msg}")

    def _open_add_server_dialog(self):
        """弹出独立窗口来手动添加私服"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("增加私服")
        dialog.geometry("380x220")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.configure(fg_color="#ffffff")

        dialog.update_idletasks()
        x = int(self.winfo_x() + (self.winfo_width() / 2) - 190)
        y = int(self.winfo_y() + (self.winfo_height() / 2) - 110)
        dialog.geometry(f"380x220+{x}+{y}")
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="手动添加私服",
            font=("Microsoft YaHei", 16, "bold"), text_color="#333333"
        ).grid(row=0, column=0, pady=(20, 15))

        ctk.CTkLabel(
            dialog, text="私服名称",
            font=("Microsoft YaHei", 12), text_color="#333333"
        ).grid(row=1, column=0, padx=30, pady=(5, 2), sticky="w")

        name_entry = ctk.CTkEntry(
            dialog, width=320, height=32,
            placeholder_text="例如：帆船[广州]", corner_radius=8
        )
        name_entry.grid(row=2, column=0, padx=30, pady=2)

        ctk.CTkLabel(
            dialog, text="域名（不含 https:// 和末尾 /，需包含端口）",
            font=("Microsoft YaHei", 12), text_color="#333333"
        ).grid(row=3, column=0, padx=30, pady=(8, 2), sticky="w")

        addr_entry = ctk.CTkEntry(
            dialog, width=320, height=32,
            placeholder_text="例如：gz.fcaugame.cn:443", corner_radius=8
        )
        addr_entry.grid(row=4, column=0, padx=30, pady=2)

        ctk.CTkLabel(
            dialog,
            text="注意：域名需包含端口号，如 :443",
            font=("Microsoft YaHei", 10), text_color="#999999"
        ).grid(row=5, column=0, padx=30, pady=(2, 5), sticky="w")

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=6, column=0, pady=(5, 15))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        def on_confirm():
            name = (name_entry.get() or "").strip()
            addr = (addr_entry.get() or "").strip()
            if not name or not addr:
                messagebox.showwarning("提示", "请填写私服名称和域名！", parent=dialog)
                return
            if ":" not in addr:
                messagebox.showerror("错误", "域名需要包含端口，例如：gz.fcaugame.cn:443", parent=dialog)
                return
            host_port = addr.split(":", 1)
            try:
                int(host_port[1].strip())
            except Exception:
                messagebox.showerror("错误", "端口号无效。", parent=dialog)
                return
            self._add_manual_server_to_list(name, addr)
            dialog.destroy()

        ctk.CTkButton(
            btn_frame, text="取消", width=120, height=32, corner_radius=8,
            font=("Microsoft YaHei", 12),
            fg_color="#6c757d", hover_color="#5a6268",
            command=dialog.destroy
        ).grid(row=0, column=0, padx=(10, 5))

        ctk.CTkButton(
            btn_frame, text="确认添加", width=120, height=32, corner_radius=8,
            font=("Microsoft YaHei", 12),
            fg_color="#28a745", hover_color="#218838",
            command=on_confirm
        ).grid(row=0, column=1, padx=(5, 10))

        name_entry.focus_set()

    def _add_manual_server_to_list(self, name, addr):
        """将手动添加的私服写入 self.servers_remote_items 并刷新 UI"""
        name = (name or "").strip()
        addr = (addr or "").strip()

        self.servers_remote_items[name] = addr

        selected = {n for n, cb in self.servers_checkboxes.items() if (cb.get() is True or cb.get() == 1)}
        manual_names = {n for n in self.servers_remote_items if n not in self.servers_checkboxes}
        self._rebuild_servers_checkboxes(selected, manual_names)

    def _apply_servers_to_region_info(self):
        """应用：把勾选的私服写入 regionInfo.json"""
        selected = []
        for name, cb in self.servers_checkboxes.items():
            try:
                if cb.get() == 1 or cb.get() is True:
                    selected.append(name)
            except Exception:
                pass

        if not selected and len(self.servers_checkboxes) > 0:
            messagebox.showwarning("提示", "请至少勾选一个私服再点击[应用]。")
            return

        userprofile = os.environ.get("USERPROFILE", "")
        region_dir = os.path.join(userprofile, "AppData", "LocalLow", "Innersloth", "Among Us")
        region_file = os.path.join(region_dir, "regionInfo.json")

        if not os.path.isdir(region_dir):
            messagebox.showerror(
                "错误",
                "未检测到 Among Us 存档目录，请确认游戏已运行过一次：\n\n" + region_dir
            )
            return

        base = None
        if os.path.isfile(region_file):
            try:
                try:
                    os.chmod(region_file, stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass
                with open(region_file, "r", encoding="utf-8-sig") as f:
                    base = json.load(f)
            except Exception as e:
                messagebox.showerror(
                    "读取失败",
                    f"无法读取 regionInfo.json，请关闭游戏后重试：\n\n{region_file}\n\n错误：{e}"
                )
                return

        if not isinstance(base, dict):
            base = {
                "CurrentRegionIdx": 3,
                "Regions": []
            }

        regions = base.get("Regions")
        if not isinstance(regions, list):
            regions = []
            base["Regions"] = regions

        # 删除被取消勾选的私服
        for name in list(self.servers_remote_items.keys()):
            if name in selected:
                continue
            regions = [r for r in regions if r.get("Name") != name]

        # 写入勾选的私服
        for name in selected:
            addr = self.servers_remote_items.get(name, "")
            host = ""
            port = 443
            if ":" in addr:
                hp = addr.split(":", 1)
                host = hp[0].strip()
                try:
                    port = int(hp[1].strip())
                except Exception:
                    pass

            item = {
                "$type": "StaticHttpRegionInfo, Assembly-CSharp",
                "Name": name,
                "PingServer": host,
                "Servers": [
                    {
                        "Name": "http-1",
                        "Ip": host,
                        "Port": port,
                        "UseDtls": False,
                        "Players": 0,
                        "ConnectionFailures": 0
                    }
                ],
                "TargetServer": None,
                "TranslateName": 1003
            }
            regions = [r for r in regions if r.get("Name") != name]
            regions.append(item)

        base["Regions"] = regions

        # 备份
        try:
            bak = region_file + ".bak"
            with open(bak, "w", encoding="utf-8") as f:
                json.dump(base, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

        # 写回
        try:
            with open(region_file, "w", encoding="utf-8") as f:
                json.dump(base, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror(
                "写入失败",
                f"无法写入 regionInfo.json，请确认目录可写且未被占用：\n\n{region_file}\n\n错误：{e}"
            )
            return

        messagebox.showinfo(
            "应用成功",
            f"已将 {len(selected)} 个私服写入 regionInfo.json：\n"
            f"· 游戏存档目录：\n{region_dir}\n"
            f"· 文件：regionInfo.json\n\n"
            "请重启 Among Us 使配置生效。"
        )

    def refresh_path_list(self):
        """刷新路径列表显示"""
        if not hasattr(self, 'path_list_frame'):
            return

        for widget in self.path_list_frame.winfo_children():
            widget.destroy()

        if not self.game_root_paths:
            ctk.CTkLabel(
                self.path_list_frame, text="暂无游戏路径，请添加",
                font=("Microsoft YaHei", 12), text_color="#888888"
            ).grid(row=0, column=0, pady=20)
            return

        for idx, path in enumerate(self.game_root_paths):
            path_item = ctk.CTkFrame(
                self.path_list_frame, fg_color="#e0e0e0", corner_radius=8, height=40
            )
            path_item.grid(row=idx, column=0, padx=5, pady=3, sticky="ew")
            path_item.grid_columnconfigure(0, weight=1)
            path_item.grid_propagate(False)

            path_label = ctk.CTkLabel(
                path_item, text=path, font=("Microsoft YaHei", 11),
                anchor="w", text_color="#333333"
            )
            path_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")

            delete_btn = ctk.CTkButton(
                path_item, text="删除", width=50, height=28, corner_radius=6,
                font=("Microsoft YaHei", 11),
                fg_color="#dc3545", hover_color="#c82333",
                command=lambda p=path: self.remove_game_path(p)
            )
            delete_btn.grid(row=0, column=1, padx=5, pady=6)

    def add_game_path(self):
        """添加游戏路径（智能解析，支持单个游戏目录）"""
        logger.user_action("用户点击添加路径按钮")
        path = self.path_display.get().strip()

        if not path:
            logger.debug("路径输入框为空，打开选择文件夹对话框")
            selected_path = filedialog.askdirectory(title="选择游戏目录")
            if selected_path:
                self.path_display.delete(0, "end")
                self.path_display.insert(0, selected_path)
                path = selected_path
                logger.user_action(f"用户选择路径: {path}")
                self.save_config()
            else:
                logger.debug("用户取消选择路径")
            return

        if not os.path.isdir(path):
            logger.warning(f"路径无效: {path}")
            messagebox.showerror("错误", "路径无效或不是一个文件夹！")
            return

        norm_path = os.path.normpath(path)
        if any(os.path.normpath(p) == norm_path for p in self.game_root_paths):
            logger.warning(f"路径已存在: {path}")
            messagebox.showwarning("提示", "该路径已存在！")
            return

        logger.debug(f"开始分析路径: {path}")

        if self.has_game_subdirs(path):
            logger.info(f"检测到游戏根目录: {path}")
            self._add_path_to_list(path)
            return

        if self.is_game_dir(path):
            logger.info(f"检测到单个游戏目录: {path}")
            parent_dir = os.path.dirname(path)
            game_name = os.path.basename(path)
            if parent_dir and os.path.isdir(parent_dir):
                norm_parent = os.path.normpath(parent_dir)
                if any(os.path.normpath(p) == norm_parent for p in self.game_root_paths):
                    logger.info(f"父目录已存在: {parent_dir}")
                    messagebox.showinfo("提示", f"该游戏的父目录已添加：\n\n{parent_dir}\n\n游戏版本：{game_name}")
                    return
                result = messagebox.askyesno(
                    "检测到单个游戏",
                    f"您选择的是单个游戏目录：\n{game_name}\n\n"
                    f"将添加其父目录作为游戏根目录：\n{parent_dir}\n\n"
                    f"是否继续？"
                )
                if result:
                    logger.user_action(f"用户确认添加父目录: {parent_dir}")
                    self._add_path_to_list(parent_dir)
                else:
                    logger.user_action("用户取消添加父目录")
            else:
                self._add_path_to_list(path)
            return

        logger.debug("当前目录不是游戏目录，尝试智能解析...")
        resolved, desc = self.resolve_game_root(path)
        if resolved:
            norm_resolved = os.path.normpath(resolved)
            already_exists = any(os.path.normpath(p) == norm_resolved for p in self.game_root_paths)
            if already_exists:
                logger.info(f"解析后的路径已存在: {resolved}")
                messagebox.showinfo("提示", f"检测到该路径的游戏根目录已存在：\n\n{resolved}")
                return
            result = messagebox.askyesno(
                "路径智能解析",
                f"在所选目录中未直接找到游戏文件。\n\n"
                f"但在{desc}找到了游戏目录：\n{resolved}\n\n"
                f"是否使用此路径？"
            )
            if result:
                logger.user_action(f"用户确认使用解析路径: {resolved}")
                self._add_path_to_list(resolved)
            else:
                logger.user_action("用户取消使用解析路径，保留原路径")
                self._add_path_to_list(path)
        else:
            logger.warning(f"未找到游戏文件: {path}")
            result = messagebox.askyesno(
                "未找到游戏",
                f"在所选目录及其上下级目录中均未找到游戏文件。\n\n"
                f"路径：{path}\n\n"
                f"是否仍然添加此路径？"
            )
            if result:
                logger.user_action(f"用户确认添加无游戏路径: {path}")
                self._add_path_to_list(path)
            else:
                logger.user_action("用户取消添加无游戏路径")

    def _add_path_to_list(self, path):
        """将路径添加到列表（内部方法）"""
        logger.info(f"添加路径到列表: {path}")
        self.game_root_paths.append(path)
        self.save_config()
        self.refresh_path_list()
        self.scan_game_versions(show_msg=False)
        self.path_display.delete(0, "end")
        messagebox.showinfo("成功", f"已添加路径：\n{path}")

    def remove_game_path(self, path):
        """删除游戏路径"""
        logger.user_action(f"用户请求删除路径: {path}")
        result = messagebox.askyesno("确认删除", f"确定要删除此路径吗？\n\n{path}")
        if result:
            logger.user_action(f"用户确认删除路径: {path}")
            if path in self.game_root_paths:
                self.game_root_paths.remove(path)
                self.save_config()
                self.refresh_path_list()
                self.scan_game_versions(show_msg=False)
        else:
            logger.user_action("用户取消删除路径")

    def setup_settings_update_tab(self):
        """更新标签页"""
        update_frame = self.settings_tabview.tab("更新")
        update_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            update_frame, text="检查更新",
            font=("Microsoft YaHei", 18, "bold"), text_color="#333333"
        ).grid(row=0, column=0, pady=15)

        self.check_update_button = ctk.CTkButton(
            update_frame, text="检查启动器更新", width=220, height=40, corner_radius=10,
            font=("Microsoft YaHei", 14),
            fg_color="#5a8ab5", hover_color="#4a7a9b",
            command=self.check_update
        )
        self.check_update_button.grid(row=1, column=0, pady=10)

        ctk.CTkLabel(
            update_frame, text=f"当前版本：{self.current_version}",
            font=("Microsoft YaHei", 12), text_color="#000000"
        ).grid(row=2, column=0, pady=5)

    def setup_settings_buttons_tab(self):
        """按钮显示标签页"""
        buttons_frame = self.settings_tabview.tab("按钮显示")
        buttons_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            buttons_frame, text="主界面按钮显示设置",
            font=("Microsoft YaHei", 18, "bold"), text_color="#333333"
        ).grid(row=0, column=0, pady=20)

        ctk.CTkLabel(
            buttons_frame, text="选择要在启动页面上显示的按钮：",
            font=("Microsoft YaHei", 12), text_color="#000000"
        ).grid(row=1, column=0, pady=(5, 15))

        self.addons_checkbox = ctk.CTkCheckBox(
            buttons_frame, text="打开插件文件夹", font=("Microsoft YaHei", 13),
            checkbox_width=22, checkbox_height=22, corner_radius=5,
            onvalue=True, offvalue=False, command=self.on_button_visibility_change
        )
        self.addons_checkbox.grid(row=2, column=0, pady=10)
        self.addons_checkbox.select() if self.button_visibility["addons"] else self.addons_checkbox.deselect()

        self.presets_checkbox = ctk.CTkCheckBox(
            buttons_frame, text="打开预设文件夹", font=("Microsoft YaHei", 13),
            checkbox_width=22, checkbox_height=22, corner_radius=5,
            onvalue=True, offvalue=False, command=self.on_button_visibility_change
        )
        self.presets_checkbox.grid(row=3, column=0, pady=10)
        self.presets_checkbox.select() if self.button_visibility["presets"] else self.presets_checkbox.deselect()

        ctk.CTkLabel(
            buttons_frame, text="更改后立即生效",
            text_color="#aaaaaa", font=("Microsoft YaHei", 11)
        ).grid(row=4, column=0, pady=20)

    def setup_settings_about_tab(self):
        """关于标签页"""
        about_frame = self.settings_tabview.tab("关于")
        about_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            about_frame, text="关于 NoS Launcher",
            font=("Microsoft YaHei", 18, "bold"), text_color="#333333"
        ).grid(row=0, column=0, pady=20)

        ctk.CTkLabel(
            about_frame, text="绿林Greenwoo制作",
            font=("Microsoft YaHei", 15, "bold"), text_color="#333333"
        ).grid(row=1, column=0, pady=10)

        export_log_btn = ctk.CTkButton(
            about_frame, text="导出日志", width=120, height=32, corner_radius=8,
            font=("Microsoft YaHei", 12),
            fg_color="#5a8ab5", hover_color="#4a7a9b", command=self.export_log
        )
        export_log_btn.grid(row=2, column=0, pady=10)

        link_label = ctk.CTkLabel(
            about_frame, text="GitHub项目链接",
            font=("Microsoft YaHei", 13), text_color="#5a8ab5", cursor="hand2"
        )
        link_label.grid(row=3, column=0, pady=10)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/MHW-YTT/NOS_Launcher"))

    def export_log(self):
        """导出日志到文件"""
        logger.user_action("用户点击导出日志按钮")
        filepath = filedialog.asksaveasfilename(
            title="导出日志", defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=f"nos_launcher_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filepath:
            if logger.export_to_file(filepath):
                messagebox.showinfo("成功", f"日志已导出到：\n{filepath}")
                logger.info(f"日志导出成功: {filepath}")
            else:
                messagebox.showerror("错误", "导出日志失败！")
                logger.error("日志导出失败")
        else:
            logger.debug("用户取消了日志导出")

    # ========================================================
    # Logo 加载
    # ========================================================
    def load_logo(self):
        try:
            logo_url = "https://auojplay.fanchuanovo.cn/NoS_Launcher/re/nos.png"
            response = requests.get(logo_url, timeout=5)
            response.raise_for_status()

            pil_image = Image.open(BytesIO(response.content))
            max_width = 380
            original_width, original_height = pil_image.size

            if original_width > max_width:
                scale_ratio = max_width / original_width
                new_height = int(original_height * scale_ratio)
                new_width = max_width
            else:
                new_width = original_width
                new_height = original_height

            logo_image = ctk.CTkImage(
                light_image=pil_image, dark_image=pil_image,
                size=(new_width, new_height)
            )

            self.logo_label = ctk.CTkLabel(
                master=self.logo_frame, image=logo_image, text=""
            )
            self.logo_label.grid(row=0, column=0, pady=5)
            self.logo_image = logo_image
        except Exception as e:
            print(f"从网络加载 Logo 失败: {e}")
            self.show_text_logo("NoS Launcher")

    def show_text_logo(self, text):
        self.logo_label = ctk.CTkLabel(
            master=self.logo_frame, text=text,
            font=("Microsoft YaHei", 28, "bold"), text_color="#ffffff"
        )
        self.logo_label.grid(row=0, column=0, pady=5)

    # ========================================================
    # 配置加载/保存
    # ========================================================
    def load_config(self):
        logger.info("开始加载配置文件...")
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                old_path = config.get("game_path", "")
                if old_path and isinstance(old_path, str):
                    self.game_root_paths = [old_path]
                    logger.info(f"从旧版配置迁移路径: {old_path}")
                else:
                    self.game_root_paths = config.get("game_paths", [])
                    logger.info(f"加载游戏路径列表: {self.game_root_paths}")

                saved_visibility = config.get("button_visibility", {})
                self.button_visibility["addons"] = saved_visibility.get("addons", True)
                self.button_visibility["presets"] = saved_visibility.get("presets", True)

                self.addon_versions = config.get("addon_versions", {})
                self.last_selected_version = config.get("last_selected_version", "")

                self.steam_path_saved = config.get("steam_path", "")
                if self.steam_path_saved:
                    logger.info(f"加载Steam路径: {self.steam_path_saved}")

                if self.game_root_paths:
                    self.scan_game_versions(show_msg=False)
                logger.info("配置文件加载完成")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        else:
            logger.info("配置文件不存在，将创建新配置")

        self.check_steam_game_directory()

    def check_steam_game_directory(self):
        """检查保存的目录中是否有Steam的游戏目录"""
        logger.debug("检查Steam游戏目录...")
        steam_path = self.get_steam_path()
        if not steam_path:
            logger.debug("未检测到Steam安装")
            return

        steam_dir = os.path.dirname(steam_path)
        common_path = os.path.join(steam_dir, "steamapps", "common")
        logger.debug(f"Steam common路径: {common_path}")

        if not os.path.isdir(common_path):
            logger.debug("Steam common目录不存在")
            return

        norm_common = os.path.normpath(common_path)
        for p in self.game_root_paths:
            if os.path.normpath(p) == norm_common:
                logger.debug("Steam路径已在游戏目录列表中")
                return

        among_us_found = False
        try:
            for item in os.listdir(common_path):
                item_path = os.path.join(common_path, item)
                if os.path.isdir(item_path):
                    among_us_exe = os.path.join(item_path, "Among Us.exe")
                    among_us_data = os.path.join(item_path, "Among Us_Data")
                    if os.path.exists(among_us_exe) or os.path.exists(among_us_data):
                        among_us_found = True
                        logger.info(f"在Steam目录发现游戏: {item}")
                        break
        except Exception as e:
            logger.error(f"扫描Steam目录失败: {e}")

        if among_us_found:
            logger.info("提示用户添加Steam游戏路径")
            result = messagebox.askyesno(
                "发现Steam游戏",
                f"检测到Steam目录下有Among Us游戏，\n"
                f"但当前游戏目录列表中没有Steam路径。\n\n"
                f"是否添加以下路径？\n{common_path}"
            )
            if result:
                logger.user_action(f"用户确认添加Steam路径: {common_path}")
                self.game_root_paths.append(common_path)
                self.save_config()
                self.scan_game_versions(show_msg=True)
                if hasattr(self, 'path_list_frame'):
                    self.refresh_path_list()
            else:
                logger.user_action("用户取消添加Steam路径")

    def save_config(self):
        logger.debug("保存配置文件...")
        try:
            steam_path = self.get_steam_path()
            config = {
                "game_paths": self.game_root_paths,
                "button_visibility": self.button_visibility,
                "addon_versions": self.addon_versions,
                "last_selected_version": self.last_selected_version,
                "steam_path": steam_path if steam_path else ""
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            logger.debug(f"配置已保存: {config}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    # ========================================================
    # 插件市场功能
    # ========================================================
    def load_addon_list(self):
        """加载插件列表"""
        if not hasattr(self, 'addon_list_frame'):
            return

        for widget in self.addon_list_frame.winfo_children():
            widget.destroy()

        loading_label = ctk.CTkLabel(
            self.addon_list_frame, text="正在加载插件列表...",
            font=("Microsoft YaHei", 12), text_color="#888888"
        )
        loading_label.grid(row=0, column=0, pady=20)

        threading.Thread(target=self._fetch_addon_list, daemon=True).start()

    def _fetch_addon_list(self):
        try:
            response = requests.get("https://auojplay.fanchuanovo.cn/NoS_Launcher/addons/list.json", timeout=10)
            response.raise_for_status()
            addon_data = response.json()
            self.after(0, lambda: self._display_addon_list(addon_data))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._show_addon_list_error(error_msg))

    def _display_addon_list(self, addon_data):
        if not hasattr(self, 'addon_list_frame'):
            return

        for widget in self.addon_list_frame.winfo_children():
            widget.destroy()

        if not addon_data:
            ctk.CTkLabel(
                self.addon_list_frame, text="暂无可用插件",
                font=("Microsoft YaHei", 12), text_color="#888888"
            ).grid(row=0, column=0, pady=20)
            return

        self.addon_data = addon_data
        selected_display = self.version_combobox.get()
        addons_path = None

        if selected_display not in ["请先在设置中添加文件夹", "未找到有效版本"]:
            real_name, game_root = self.get_version_info(selected_display)
            if game_root:
                addons_path = os.path.join(game_root, real_name, "Addons")

        for idx, (key, url) in enumerate(addon_data.items()):
            addon_name = key
            cloud_version = ""
            if "name:" in key:
                parts = key.split("|")
                for part in parts:
                    if part.startswith("name:"):
                        addon_name = part[5:]
                    elif part.startswith("ver:"):
                        cloud_version = part[4:]

            filename = url.split("/")[-1]
            if not filename or not filename.lower().endswith('.zip'):
                filename = f"{addon_name}.zip"

            is_installed = False
            need_update = False

            if addons_path and os.path.isdir(addons_path):
                plugin_file = os.path.join(addons_path, filename)
                is_installed = os.path.exists(plugin_file)
                if is_installed and cloud_version:
                    local_version = self.addon_versions.get(addon_name, "")
                    need_update = local_version != cloud_version

            addon_item = ctk.CTkFrame(
                self.addon_list_frame, fg_color="#5a7a8a", corner_radius=10, height=50
            )
            addon_item.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            addon_item.grid_columnconfigure(0, weight=1)
            addon_item.grid_propagate(False)

            display_text = addon_name
            if cloud_version:
                display_text = f"{addon_name} (v{cloud_version})"

            name_label = ctk.CTkLabel(
                addon_item, text=display_text,
                font=("Microsoft YaHei", 13), anchor="w", text_color="#ffffff"
            )
            name_label.grid(row=0, column=0, padx=18, pady=12, sticky="w")

            if need_update:
                download_btn = ctk.CTkButton(
                    addon_item, text="更新", width=65, height=30, corner_radius=8,
                    font=("Microsoft YaHei", 12),
                    fg_color="#ffc107", hover_color="#e0a800", text_color="#000000",
                    command=lambda n=addon_name, u=url, v=cloud_version: self.download_addon_with_version(n, u, v)
                )
            elif is_installed:
                download_btn = ctk.CTkButton(
                    addon_item, text="已安装", width=75, height=30, corner_radius=8,
                    font=("Microsoft YaHei", 12),
                    fg_color="#6c757d", hover_color="#5a6268",
                    command=lambda n=addon_name, u=url, v=cloud_version: self.download_addon_with_version(n, u, v)
                )
            else:
                download_btn = ctk.CTkButton(
                    addon_item, text="下载", width=65, height=30, corner_radius=8,
                    font=("Microsoft YaHei", 12),
                    fg_color="#28a745", hover_color="#218838",
                    command=lambda n=addon_name, u=url, v=cloud_version: self.download_addon_with_version(n, u, v)
                )
            download_btn.grid(row=0, column=1, padx=12, pady=10)

    def _show_addon_list_error(self, error_msg):
        if not hasattr(self, 'addon_list_frame'):
            return

        for widget in self.addon_list_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.addon_list_frame, text=f"加载失败：{error_msg}",
            font=("Microsoft YaHei", 11), text_color="#ff6b6b"
        ).grid(row=0, column=0, pady=20)

        retry_btn = ctk.CTkButton(
            self.addon_list_frame, text="重试", width=80, height=30, corner_radius=10,
            font=("Microsoft YaHei", 12), command=self.load_addon_list
        )
        retry_btn.grid(row=1, column=0, pady=10)

    def download_addon_with_version(self, addon_name, addon_url, cloud_version=""):
        """带版本号的插件下载"""
        selected_display = self.version_combobox.get()
        if selected_display in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return

        real_name, game_root = self.get_version_info(selected_display)
        if not game_root:
            messagebox.showerror("错误", "无法找到游戏路径！")
            return

        if cloud_version:
            local_version = self.addon_versions.get(addon_name, "")
            if local_version == cloud_version:
                result = messagebox.askyesno(
                    "提示",
                    f"插件 {addon_name} 已是最新版本 (v{cloud_version})\n\n是否重新下载？"
                )
                if not result:
                    return

        download_window = DownloadWindow(self, f"下载插件 - {addon_name}")
        download_window.log(f"插件名称: {addon_name}")
        if cloud_version:
            download_window.log(f"版本号: {cloud_version}")
        download_window.log("-" * 50)
        download_window.set_status("正在连接服务器...")

        def download_thread():
            try:
                addons_path = os.path.join(game_root, real_name, "Addons")
                if not os.path.isdir(addons_path):
                    os.makedirs(addons_path)
                download_window.log(f"创建目录: {addons_path}")

                filename = addon_url.split("/")[-1]
                if not filename or not filename.lower().endswith('.zip'):
                    filename = f"{addon_name}.zip"
                final_path = os.path.join(addons_path, filename)
                download_window.log(f"保存路径: {final_path}")

                response = requests.get(addon_url, stream=True, timeout=30)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                download_window.log(f"文件大小: {total_size / 1024:.2f} KB")
                download_window.log("开始下载...")

                with open(final_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = downloaded / total_size
                                download_window.after(0, lambda p=progress: download_window.set_progress(p))
                                download_window.after(0, lambda d=downloaded, t=total_size: download_window.set_status(f"下载中... {d}/{t} bytes"))

                download_window.log("下载完成！")

                if cloud_version:
                    self.addon_versions[addon_name] = cloud_version
                    self.save_config()
                    download_window.log(f"已记录版本: v{cloud_version}")

                download_window.log("-" * 50)
                download_window.set_status("下载完成！")
                download_window.set_progress(1)
                download_window.after(0, lambda: download_window.show_close_button())
                download_window.after(0, lambda: messagebox.showinfo("成功", f"插件 {addon_name} 下载成功！"))
                self.after(0, self.load_addon_list)
            except Exception as e:
                download_window.log(f"下载失败: {e}")
                download_window.set_status(f"下载失败: {e}")
                download_window.after(0, lambda: download_window.show_close_button())

        threading.Thread(target=download_thread, daemon=True).start()

    def download_addon(self, addon_name, addon_url):
        """兼容旧版下载方法"""
        self.download_addon_with_version(addon_name, addon_url, "")

    # ========================================================
    # 下载游戏功能
    # ========================================================
    def load_game_list(self):
        """加载游戏列表"""
        if not hasattr(self, 'game_list_frame'):
            return

        for widget in self.game_list_frame.winfo_children():
            widget.destroy()

        loading_label = ctk.CTkLabel(
            self.game_list_frame, text="正在加载游戏列表...",
            font=("Microsoft YaHei", 12), text_color="#888888"
        )
        loading_label.grid(row=0, column=0, pady=20)

        threading.Thread(target=self._fetch_game_list, daemon=True).start()

    def _fetch_game_list(self):
        try:
            response = requests.get("https://auojplay.fanchuanovo.cn/NoS_Launcher/all_in_one/url.json", timeout=10)
            response.raise_for_status()
            game_data = response.json()
            self.after(0, lambda: self._display_game_list(game_data))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._show_game_list_error(error_msg))

    def _display_game_list(self, game_data):
        if not hasattr(self, 'game_list_frame'):
            return

        for widget in self.game_list_frame.winfo_children():
            widget.destroy()

        if not game_data:
            ctk.CTkLabel(
                self.game_list_frame, text="暂无可用游戏版本",
                font=("Microsoft YaHei", 12), text_color="#888888"
            ).grid(row=0, column=0, pady=20)
            return

        self.game_data = game_data
        for idx, (name, url) in enumerate(game_data.items()):
            game_item = ctk.CTkFrame(
                self.game_list_frame, fg_color="#5a7a8a", corner_radius=10, height=50
            )
            game_item.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            game_item.grid_columnconfigure(0, weight=1)
            game_item.grid_propagate(False)

            name_label = ctk.CTkLabel(
                game_item, text=name,
                font=("Microsoft YaHei", 13), anchor="w", text_color="#ffffff"
            )
            name_label.grid(row=0, column=0, padx=18, pady=12, sticky="w")

            download_btn = ctk.CTkButton(
                game_item, text="下载", width=65, height=30, corner_radius=8,
                font=("Microsoft YaHei", 12),
                fg_color="#28a745", hover_color="#218838",
                command=lambda n=name, u=url: self.download_game(n, u)
            )
            download_btn.grid(row=0, column=1, padx=12, pady=10)

    def _show_game_list_error(self, error_msg):
        if not hasattr(self, 'game_list_frame'):
            return

        for widget in self.game_list_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.game_list_frame, text=f"加载失败：{error_msg}",
            font=("Microsoft YaHei", 11), text_color="#ff6b6b"
        ).grid(row=0, column=0, pady=20)

        retry_btn = ctk.CTkButton(
            self.game_list_frame, text="重试", width=80, height=30, corner_radius=10,
            font=("Microsoft YaHei", 12), command=self.load_game_list
        )
        retry_btn.grid(row=1, column=0, pady=10)

    def download_game(self, game_name, game_url):
        """下载游戏"""
        if not self.game_root_paths:
            messagebox.showwarning("提示", "请先在设置中添加游戏目录！")
            return

        selected_display = self.version_combobox.get()
        if selected_display in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先在启动页面选择一个游戏版本！")
            return

        real_name, game_root = self.get_version_info(selected_display)
        if not game_root:
            messagebox.showerror("错误", "无法找到游戏路径！")
            return

        target_dir = os.path.join(game_root, real_name)

        result = messagebox.askyesno(
            "确认安装",
            f"是否将游戏安装到以下目录？\n\n"
            f"游戏版本: {game_name}\n"
            f"安装目录: {target_dir}\n\n"
            f"注意：如果这不是您想安装的目录，\n"
            f"请点击【否】返回启动页面重新选择游戏版本！"
        )
        if not result:
            self.switch_page("launch")
            return

        download_window = DownloadWindow(self, f"下载游戏 - {game_name}")
        download_window.log(f"游戏版本: {game_name}")
        download_window.log(f"安装目录: {target_dir}")
        download_window.log("-" * 50)
        download_window.set_status("正在连接服务器...")

        def download_thread():
            try:
                temp_zip = os.path.join(game_root, f"_temp_{game_name}.zip")
                response = requests.get(game_url, stream=True, timeout=60)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                download_window.log(f"文件大小: {total_size / 1024 / 1024:.2f} MB")
                download_window.log("开始下载...")

                with open(temp_zip, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = downloaded / total_size
                                download_window.after(0, lambda p=progress: download_window.set_progress(p * 0.85))
                                downloaded_mb = downloaded / 1024 / 1024
                                total_mb = total_size / 1024 / 1024
                                download_window.after(0, lambda d=downloaded_mb, t=total_mb: download_window.set_status(f"下载中... {d:.2f}/{t:.2f} MB"))

                download_window.log("下载完成！")
                download_window.log("-" * 50)

                addons_path = os.path.join(target_dir, "Addons")
                if os.path.exists(addons_path):
                    download_window.log("正在删除旧的Addons文件夹...")
                    download_window.set_status("正在删除旧的Addons文件夹...")
                    try:
                        shutil.rmtree(addons_path)
                        download_window.log("Addons文件夹已删除")
                    except Exception as e:
                        download_window.log(f"删除Addons文件夹失败: {e}")

                download_window.log("正在解压...")
                download_window.set_status("正在解压文件...")

                extracted_count = 0
                replaced_count = 0
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    total_files = len(file_list)
                    for i, file_name in enumerate(file_list):
                        try:
                            file_info = zip_ref.getinfo(file_name)
                            if file_info.is_dir():
                                continue

                            target_path = os.path.join(target_dir, file_name)
                            target_file_dir = os.path.dirname(target_path)
                            if not os.path.exists(target_file_dir):
                                os.makedirs(target_file_dir)

                            if os.path.exists(target_path):
                                replaced_count += 1

                            with zip_ref.open(file_name) as source, open(target_path, 'wb') as target:
                                target.write(source.read())
                            extracted_count += 1

                            if total_files > 0:
                                file_progress = (i + 1) / total_files
                                download_window.after(0, lambda fp=file_progress: download_window.set_progress(0.85 + fp * 0.15))
                                download_window.after(0, lambda ec=extracted_count, tf=total_files: download_window.set_status(f"解压中... {ec}/{tf} 文件"))
                        except Exception as e:
                            download_window.log(f"解压 {file_name} 失败: {e}")

                try:
                    os.remove(temp_zip)
                except:
                    pass

                download_window.log(f"解压完成！")
                download_window.log(f"共解压 {extracted_count} 个文件")
                if replaced_count > 0:
                    download_window.log(f"替换了 {replaced_count} 个已存在的文件")
                download_window.log("-" * 50)
                download_window.set_status("安装完成！")
                download_window.set_progress(1)
                download_window.after(0, lambda: download_window.show_close_button())
                download_window.after(0, lambda: messagebox.showinfo("成功", f"游戏 {game_name} 安装成功！\n\n安装目录: {target_dir}\n解压文件: {extracted_count} 个\n替换文件: {replaced_count} 个"))
                self.after(0, self.scan_game_versions, (False,))
            except Exception as e:
                download_window.log(f"下载/解压失败: {e}")
                download_window.set_status(f"失败: {e}")
                download_window.after(0, lambda: download_window.show_close_button())

        threading.Thread(target=download_thread, daemon=True).start()

    # ========================================================
    # 其他功能
    # ========================================================
    def on_button_visibility_change(self):
        if hasattr(self, 'addons_checkbox'):
            self.button_visibility["addons"] = self.addons_checkbox.get()
        if hasattr(self, 'presets_checkbox'):
            self.button_visibility["presets"] = self.presets_checkbox.get()
        self.save_config()
        self.update_main_buttons_visibility()

    def update_main_buttons_visibility(self):
        selected_display = self.version_combobox.get()
        is_nos = False
        if selected_display not in ["请先在设置中添加文件夹", "未找到有效版本"]:
            real_display = selected_display.replace(" [原版]", "").replace(" [H系]", "")
            if self.version_types.get(real_display) == "nos":
                is_nos = True
        if self.current_versions and is_nos:
            if self.button_visibility["addons"]:
                self.addons_button.grid()
            else:
                self.addons_button.grid_remove()
            if self.button_visibility["presets"]:
                self.presets_button.grid()
            else:
                self.presets_button.grid_remove()
        else:
            self.addons_button.grid_remove()
            self.presets_button.grid_remove()

    def browse_folder(self):
        selected_path = filedialog.askdirectory(title="选择游戏根目录")
        if selected_path:
            self.path_display.delete(0, "end")
            self.path_display.insert(0, selected_path)

    def on_version_changed(self, value):
        """版本选择变化时，保存到配置"""
        if value and value not in ["请先在设置中添加文件夹", "未找到有效版本"]:
            self.last_selected_version = value
            self.save_config()
            self.update_main_buttons_visibility()

    def is_game_dir(self, folder_path):
        """判断一个文件夹是否是有效的游戏目录"""
        nebula_dll = os.path.join(folder_path, "BepInEx", "nebula", "Nebula.dll")
        among_us_data = os.path.join(folder_path, "Among Us_Data")
        among_us_exe = os.path.join(folder_path, "Among Us.exe")
        return os.path.exists(nebula_dll) or os.path.exists(among_us_data) or os.path.exists(among_us_exe)

    def has_game_subdirs(self, folder_path):
        """判断一个文件夹是否包含游戏子目录"""
        try:
            for item in os.listdir(folder_path):
                sub = os.path.join(folder_path, item)
                if os.path.isdir(sub) and self.is_game_dir(sub):
                    return True
        except:
            pass
        return False

    def resolve_game_root(self, user_path):
        """智能解析用户选择的路径"""
        if self.has_game_subdirs(user_path):
            return user_path, "当前目录"

        if self.is_game_dir(user_path):
            parent = os.path.dirname(user_path)
            if parent and parent != user_path and os.path.isdir(parent):
                return parent, "上级目录"
            return user_path, "当前目录（单版本）"

        current = user_path
        for i in range(1, 4):
            parent = os.path.dirname(current)
            if not parent or parent == current:
                break
            if self.has_game_subdirs(parent):
                return parent, f"向上第 {i} 层"
            current = parent

        found_roots = self._search_down_for_games(user_path, max_depth=2)
        if found_roots:
            return found_roots[0], "下级目录"
        return None, None

    def _search_down_for_games(self, folder_path, max_depth=2, current_depth=0):
        """向下递归搜索"""
        results = []
        try:
            for item in os.listdir(folder_path):
                sub = os.path.join(folder_path, item)
                if not os.path.isdir(sub):
                    continue
                if self.has_game_subdirs(sub):
                    results.append(sub)
                elif self.is_game_dir(sub):
                    if folder_path not in results:
                        results.append(folder_path)
                elif current_depth < max_depth:
                    deeper = self._search_down_for_games(sub, max_depth, current_depth + 1)
                    results.extend(deeper)
        except:
            pass

        seen = set()
        unique = []
        for r in results:
            norm = os.path.normpath(r)
            if norm not in seen:
                seen.add(norm)
                unique.append(r)
        return unique

    def scan_game_versions(self, show_msg=True):
        logger.info("开始扫描游戏版本...")
        if not hasattr(self, 'version_combobox') or not self.version_combobox:
            return

        if not self.game_root_paths:
            logger.debug("游戏路径列表为空")
            self.current_versions = []
            self.version_types = {}
            self.version_paths = {}
            self.version_combobox.configure(values=["请先在设置中添加文件夹"])
            self.version_combobox.set("请先在设置中添加文件夹")
            self.addons_button.grid_remove()
            self.presets_button.grid_remove()
            return

        try:
            versions = []
            self.version_types = {}
            self.version_paths = {}

            for game_root in self.game_root_paths:
                logger.debug(f"扫描目录: {game_root}")
                if not os.path.isdir(game_root):
                    logger.warning(f"目录不存在: {game_root}")
                    continue
                all_items = os.listdir(game_root)
                for item in all_items:
                    full_path = os.path.join(game_root, item)
                    if os.path.isdir(full_path):
                        nebula_dll_path = os.path.join(full_path, "BepInEx", "nebula", "Nebula.dll")
                        among_us_data_path = os.path.join(full_path, "Among Us_Data")

                        display_name = item
                        if item in self.version_paths:
                            parent_name = os.path.basename(game_root)
                            display_name = f"{item} ({parent_name})"

                        if os.path.exists(nebula_dll_path):
                            versions.append((display_name, item, game_root))
                            self.version_types[display_name] = "nos"
                            self.version_paths[display_name] = game_root
                            logger.debug(f"发现NoS版本: {display_name}")
                        elif os.path.exists(among_us_data_path):
                            subdirs = [d for d in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, d))]
                            if len(subdirs) == 1 and subdirs[0] == "Among Us_Data":
                                versions.append((display_name, item, game_root))
                                self.version_types[display_name] = "vanilla"
                                self.version_paths[display_name] = game_root
                                logger.debug(f"发现原版: {display_name}")
                            else:
                                versions.append((display_name, item, game_root))
                                self.version_types[display_name] = "h_series"
                                self.version_paths[display_name] = game_root
                                logger.debug(f"发现H系版本: {display_name}")

            if versions:
                versions.sort(key=lambda x: x[0])
                self.current_versions = versions

                display_versions = []
                for display_name, real_name, path in versions:
                    version_type = self.version_types.get(display_name)
                    if version_type == "vanilla":
                        display_versions.append(f"{display_name} [原版]")
                    elif version_type == "h_series":
                        display_versions.append(f"{display_name} [H系]")
                    else:
                        display_versions.append(display_name)

                self.version_combobox.configure(values=display_versions)

                version_to_set = display_versions[0]
                if self.last_selected_version:
                    if self.last_selected_version in display_versions:
                        version_to_set = self.last_selected_version
                    else:
                        clean_last = self.last_selected_version.replace(" [原版]", "").replace(" [H系]", "")
                        for dv in display_versions:
                            if dv.replace(" [原版]", "").replace(" [H系]", "") == clean_last:
                                version_to_set = dv
                                break
                self.version_combobox.set(version_to_set)
                self.update_main_buttons_visibility()

                if show_msg:
                    nos_count = sum(1 for v in self.version_types.values() if v == "nos")
                    vanilla_count = sum(1 for v in self.version_types.values() if v == "vanilla")
                    h_series_count = sum(1 for v in self.version_types.values() if v == "h_series")
                    msg = f"扫描完成，找到 {len(versions)} 个游戏版本。\n"
                    msg += f"NoS版本: {nos_count} 个\n原版: {vanilla_count} 个\nH系: {h_series_count} 个"
                    messagebox.showinfo("成功", msg)
            else:
                self.current_versions = []
                self.version_types = {}
                self.version_paths = {}
                self.version_combobox.configure(values=["未找到有效版本"])
                self.version_combobox.set("未找到有效版本")
                self.addons_button.grid_remove()
                self.presets_button.grid_remove()
                if show_msg:
                    messagebox.showwarning("警告", "未找到包含完整文件的游戏版本。")
        except Exception as e:
            messagebox.showerror("错误", f"扫描文件夹时出错：{e}")

    def get_real_version_name(self, display_name):
        """从显示名称获取真实的版本名称"""
        for suffix in [" [原版]", " [H系]"]:
            if display_name.endswith(suffix):
                return display_name[:-len(suffix)]
        return display_name

    def get_version_info(self, display_name):
        """获取版本的完整信息"""
        clean_name = self.get_real_version_name(display_name)
        for ver_display, ver_real, ver_path in self.current_versions:
            if ver_display == clean_name:
                return ver_real, ver_path
        return clean_name, self.version_paths.get(clean_name, "")

    def get_steam_path(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
            path, _ = winreg.QueryValueEx(key, "InstallPath")
            return os.path.join(path, "Steam.exe")
        except:
            return None

    def is_steam_running(self):
        try:
            output = subprocess.check_output(["tasklist"], shell=True).decode('gbk', errors='ignore')
            return "Steam.exe" in output or "steam.exe" in output
        except:
            return False

    def launch_game(self):
        logger.user_action("用户点击启动游戏")
        selected_display = self.version_combobox.get()
        if selected_display in ["请先在设置中添加文件夹", "未找到有效版本"]:
            logger.warning("未选择有效游戏版本")
            messagebox.showwarning("提示", "请先在设置中添加有效的游戏文件夹！")
            return

        real_name, game_root = self.get_version_info(selected_display)
        logger.info(f"选择版本: {real_name}, 游戏根目录: {game_root}")

        if not game_root:
            logger.error("无法找到游戏路径")
            messagebox.showerror("错误", "无法找到游戏路径！")
            return

        if not self.is_steam_running():
            logger.info("Steam未运行")
            steam_exe = self.get_steam_path()
            if steam_exe and os.path.exists(steam_exe):
                try:
                    logger.info("正在启动Steam...")
                    subprocess.Popen(steam_exe)
                    messagebox.showinfo("提示", "检测到 Steam 未运行。\n正在为你启动 Steam，请稍后重试。")
                    return
                except Exception as e:
                    logger.error(f"启动Steam失败: {e}")
            messagebox.showwarning("提示", "请先启动 Steam 后再运行游戏。")
            return

        game_dir = os.path.join(game_root, real_name)
        exe_path = os.path.join(game_dir, "Among Us.exe")

        logger.debug(f"游戏根目录: {game_root}")
        logger.debug(f"选择版本: {real_name}")
        logger.debug(f"游戏目录: {game_dir}")
        logger.debug(f"可执行文件路径: {exe_path}")
        logger.debug(f"游戏目录是否存在: {os.path.isdir(game_dir)}")
        logger.debug(f"可执行文件是否存在: {os.path.exists(exe_path)}")

        if not os.path.isdir(game_dir):
            logger.error(f"游戏目录不存在: {game_dir}")
            messagebox.showerror("错误", f"游戏目录不存在：\n{game_dir}")
            return

        if not os.path.exists(exe_path):
            possible_exes = []
            try:
                for f in os.listdir(game_dir):
                    if f.lower().endswith('.exe'):
                        possible_exes.append(f)
            except:
                pass

            if possible_exes:
                msg = f"未找到 Among Us.exe\n\n游戏目录中的可执行文件：\n"
                for exe in possible_exes:
                    msg += f" - {exe}\n"
                msg += f"\n完整路径：\n{game_dir}"
            else:
                msg = f"未找到游戏程序：\n{exe_path}\n\n游戏目录：\n{game_dir}"

            logger.error(f"未找到游戏可执行文件: {exe_path}")
            messagebox.showerror("错误", msg)
            return

        try:
            logger.info(f"启动游戏: {exe_path}")
            subprocess.Popen(exe_path, cwd=game_dir)
            logger.info("游戏启动成功")
        except Exception as e:
            logger.error(f"启动游戏失败: {e}")
            messagebox.showerror("启动失败", f"启动游戏时发生错误：\n{e}")

    def open_addons_folder(self):
        selected_display = self.version_combobox.get()
        if selected_display in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return

        real_name, game_root = self.get_version_info(selected_display)
        if not game_root:
            messagebox.showerror("错误", "无法找到游戏路径！")
            return

        addons_path = os.path.join(game_root, real_name, "Addons")
        if os.path.isdir(addons_path):
            try:
                os.startfile(addons_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：\n{e}")
        else:
            messagebox.showwarning("提示", f"插件文件夹不存在：\n{addons_path}")

    def open_presets_folder(self):
        selected_display = self.version_combobox.get()
        if selected_display in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return

        real_name, game_root = self.get_version_info(selected_display)
        if not game_root:
            messagebox.showerror("错误", "无法找到游戏路径！")
            return

        presets_path = os.path.join(game_root, real_name, "Presets")
        if os.path.isdir(presets_path):
            try:
                os.startfile(presets_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：\n{e}")
        else:
            messagebox.showwarning("提示", f"预设文件夹不存在：\n{presets_path}")

    def check_update(self):
        try:
            response = requests.get("https://auojplay.fanchuanovo.cn/NoS_Launcher/update.json", timeout=5)
            response.raise_for_status()
            update_data = response.json()
            latest_version = update_data.get("ver", "")
            download_url = update_data.get("dl", "")

            if latest_version and latest_version > self.current_version:
                result = messagebox.askyesno(
                    "发现新版本",
                    f"检测到新版本 {latest_version}\n是否立即下载更新？"
                )
                if result:
                    webbrowser.open(download_url)
            else:
                messagebox.showinfo("检查更新", "当前已是最新版本")
        except Exception as e:
            messagebox.showerror("检查更新失败", f"检查更新时出错：\n{e}")

    def check_update_on_startup(self):
        try:
            response = requests.get("https://auojplay.fanchuanovo.cn/NoS_Launcher/update.json", timeout=5)
            response.raise_for_status()
            update_data = response.json()
            latest_version = update_data.get("ver", "")
            download_url = update_data.get("dl", "")

            if latest_version and latest_version > self.current_version:
                result = messagebox.askyesno(
                    "发现新版本",
                    f"检测到新版本 {latest_version}\n当前版本：{self.current_version}\n\n是否立即下载更新？"
                )
                if result:
                    webbrowser.open(download_url)
        except:
            pass

    def auto_detect_steam_games(self):
        """自动检测Steam安装目录下的游戏"""
        try:
            steam_path = self.get_steam_path()
            if not steam_path:
                return

            steam_dir = os.path.dirname(steam_path)
            common_path = os.path.join(steam_dir, "steamapps", "common")

            if not os.path.isdir(common_path):
                return

            found_games = []
            for item in os.listdir(common_path):
                item_path = os.path.join(common_path, item)
                if os.path.isdir(item_path):
                    among_us_exe = os.path.join(item_path, "Among Us.exe")
                    among_us_data = os.path.join(item_path, "Among Us_Data")
                    if os.path.exists(among_us_exe) or os.path.exists(among_us_data):
                        found_games.append((item, item_path))

            if not found_games:
                return

            if common_path in self.game_root_paths:
                return

            result = messagebox.askyesno(
                "发现游戏",
                f"在Steam目录中发现游戏：\n\n"
                f"共找到 {len(found_games)} 个游戏\n\n"
                f"路径：{common_path}\n\n"
                f"是否添加此目录到游戏路径列表？"
            )
            if result:
                self.game_root_paths.append(common_path)
                self.save_config()
                self.scan_game_versions(show_msg=True)
                if hasattr(self, 'path_list_frame'):
                    self.refresh_path_list()
        except Exception as e:
            print(f"自动检测Steam游戏失败: {e}")

if __name__ == "__main__":
    app = NOSLauncher()
    app.mainloop()
