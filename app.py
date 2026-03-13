import customtkinter as ctk
import os
import json
import subprocess
import winreg
import hashlib
from PIL import Image
from tkinter import filedialog, messagebox
import webbrowser
import requests
from io import BytesIO
import threading

# 设置外观模式和颜色主题
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class DownloadWindow(ctk.CTkToplevel):
    """下载进度窗口"""
    def __init__(self, parent, title="下载中"):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.configure(fg_color="#2b2b2b")
        
        # 居中显示
        self.update_idletasks()
        x = int(parent.winfo_x() + (parent.winfo_width()/2) - 250)
        y = int(parent.winfo_y() + (parent.winfo_height()/2) - 200)
        self.geometry(f"500x400+{x}+{y}")
        
        # 日志区域
        self.log_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        self.log_frame.pack(fill="both", expand=True, padx=15, pady=(15, 5))
        
        self.log_textbox = ctk.CTkTextbox(
            self.log_frame, 
            width=450, 
            height=280,
            font=("Consolas", 11),
            fg_color="#1a1a1a",
            text_color="#00ff00"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 进度条区域
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=10)
        
        self.status_label = ctk.CTkLabel(
            self.progress_frame, 
            text="准备下载...", 
            font=("Microsoft YaHei", 12),
            text_color="#ffffff"
        )
        self.status_label.pack(anchor="w")
        
        self.progressbar = ctk.CTkProgressBar(
            self.progress_frame,
            width=450,
            height=15,
            corner_radius=7
        )
        self.progressbar.pack(fill="x", pady=5)
        self.progressbar.set(0)
        
        # 关闭按钮（初始隐藏）
        self.close_button = ctk.CTkButton(
            self,
            text="关闭",
            width=100,
            height=32,
            corner_radius=8,
            command=self.destroy
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
        self.game_root_path = "" 
        self.current_versions = []
        self.config_file = "config.json"
        self.current_version = "2.2.0"  # 当前启动器版本
        
        # 插件版本记录
        self.addon_versions = {}
        
        # 按钮显示配置（默认都显示）
        self.button_visibility = {
            "addons": True,    # 插件文件夹按钮
            "presets": True    # 预设文件夹按钮
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
            self.nav_frame,
            text="启动",
            width=130,
            height=36,
            corner_radius=10,
            font=("Microsoft YaHei", 14, "bold"),
            fg_color="#5a8ab5",
            hover_color="#4a7a9b",
            command=lambda: self.switch_page("launch")
        )
        self.nav_launch_btn.grid(row=0, column=0, padx=5, pady=5)

        self.nav_addon_btn = ctk.CTkButton(
            self.nav_frame,
            text="插件市场",
            width=130,
            height=36,
            corner_radius=10,
            font=("Microsoft YaHei", 14, "bold"),
            fg_color="#5a6b7a",
            hover_color="#4a5b6a",
            command=lambda: self.switch_page("addon")
        )
        self.nav_addon_btn.grid(row=0, column=1, padx=5, pady=5)

        self.nav_settings_btn = ctk.CTkButton(
            self.nav_frame,
            text="设置",
            width=130,
            height=36,
            corner_radius=10,
            font=("Microsoft YaHei", 14, "bold"),
            fg_color="#5a6b7a",
            hover_color="#4a5b6a",
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
        self.create_addon_page()
        self.create_settings_page()

        # 默认显示启动页面
        self.switch_page("launch")

        # 在所有UI元素创建后，再加载配置
        self.load_config()
        
        # 启动时自动检测更新
        self.after(1000, self.check_update_on_startup)

    def switch_page(self, page_name):
        """切换页面"""
        # 隐藏所有页面
        self.launch_page.grid_remove()
        self.addon_page.grid_remove()
        self.settings_page.grid_remove()
        
        # 重置所有导航按钮颜色
        self.nav_launch_btn.configure(fg_color="#5a6b7a")
        self.nav_addon_btn.configure(fg_color="#5a6b7a")
        self.nav_settings_btn.configure(fg_color="#5a6b7a")
        
        # 显示选中的页面并高亮对应按钮
        if page_name == "launch":
            self.launch_page.grid()
            self.nav_launch_btn.configure(fg_color="#5a8ab5")
        elif page_name == "addon":
            self.addon_page.grid()
            self.nav_addon_btn.configure(fg_color="#5a8ab5")
            # 切换到插件市场时加载列表
            self.load_addon_list()
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
            master=self.launch_page, 
            text="欢迎使用 NoS Launcher", 
            font=("Microsoft YaHei", 22, "bold"), 
            text_color="#ffffff"
        )
        self.label_title.grid(row=0, column=0, pady=(25, 5))

        # 2. 版本选择区域
        self.version_label = ctk.CTkLabel(
            master=self.launch_page, 
            text="当前游戏版本：", 
            font=("Microsoft YaHei", 14), 
            text_color="#ffffff"
        )
        self.version_label.grid(row=1, column=0, pady=(10, 5))

        self.version_combobox = ctk.CTkOptionMenu(
            master=self.launch_page, 
            values=["请先在设置中添加文件夹"], 
            width=280, 
            height=38, 
            corner_radius=10, 
            font=("Microsoft YaHei", 13), 
            dynamic_resizing=False
        )
        self.version_combobox.grid(row=2, column=0, pady=(0, 15))

        # 3. 启动按钮
        self.launch_button = ctk.CTkButton(
            master=self.launch_page, 
            text="▶  启动游戏", 
            width=280, 
            height=48, 
            corner_radius=12, 
            font=("Microsoft YaHei", 16, "bold"), 
            command=self.launch_game,
            fg_color="#5a8ab5",
            hover_color="#4a7a9b"
        )
        self.launch_button.grid(row=3, column=0, pady=12)

        # 4. 打开插件文件夹按钮
        self.addons_button = ctk.CTkButton(
            master=self.launch_page,
            text="打开插件文件夹",
            width=280,
            height=38,
            corner_radius=10,
            font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5",
            hover_color="#4a7a9b",
            command=self.open_addons_folder
        )
        self.addons_button.grid(row=4, column=0, pady=8)
        self.addons_button.grid_remove() 

        # 5. 打开预设文件夹按钮
        self.presets_button = ctk.CTkButton(
            master=self.launch_page,
            text="打开预设文件夹",
            width=280,
            height=38,
            corner_radius=10,
            font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5",
            hover_color="#4a7a9b",
            command=self.open_presets_folder
        )
        self.presets_button.grid(row=5, column=0, pady=8)
        self.presets_button.grid_remove()

        # 6. 版本号
        self.version_label_bottom = ctk.CTkLabel(
            master=self.launch_page,
            text=f"NoS Launcher {self.current_version}",
            font=("Microsoft YaHei", 11),
            text_color="#aaaaaa"
        )
        self.version_label_bottom.grid(row=6, column=0, pady=(15, 20))

    # ========================================================
    # 插件市场页面
    # ========================================================
    def create_addon_page(self):
        """创建插件市场页面"""
        self.addon_page = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.addon_page.grid(row=0, column=0, sticky="nsew")
        self.addon_page.grid_columnconfigure(0, weight=1)
        self.addon_page.grid_rowconfigure(1, weight=1)

        # 标题区域
        title_frame = ctk.CTkFrame(self.addon_page, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(15, 10), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            title_frame, 
            text="插件市场", 
            font=("Microsoft YaHei", 20, "bold"), 
            text_color="#ffffff"
        ).grid(row=0, column=0, pady=5)
        
        # 提示信息
        self.addon_tip_label = ctk.CTkLabel(
            title_frame, 
            text="下载链接由绿林Greenwoo和帆船提供", 
            font=("Microsoft YaHei", 11), 
            text_color="#aaaaaa"
        )
        self.addon_tip_label.grid(row=1, column=0, pady=(0, 5))

        # 插件列表容器
        self.addon_list_frame = ctk.CTkScrollableFrame(
            self.addon_page, 
            width=550, 
            height=320,
            corner_radius=10
        )
        self.addon_list_frame.grid(row=1, column=0, padx=25, pady=5, sticky="nsew")
        self.addon_list_frame.grid_columnconfigure(0, weight=1)

        # 进度条区域
        self.download_progress_frame = ctk.CTkFrame(self.addon_page, fg_color="transparent")
        self.download_progress_frame.grid(row=2, column=0, padx=25, pady=15, sticky="ew")
        self.download_progress_frame.grid_columnconfigure(0, weight=1)

        # 下载状态标签
        self.download_status_label = ctk.CTkLabel(
            self.download_progress_frame, 
            text="", 
            font=("Microsoft YaHei", 12),
            text_color="#aaaaaa"
        )
        self.download_status_label.grid(row=0, column=0, pady=(0, 5))

        # 进度条
        self.download_progressbar = ctk.CTkProgressBar(
            self.download_progress_frame,
            width=550,
            height=14,
            corner_radius=7
        )
        self.download_progressbar.grid(row=1, column=0, pady=2)
        self.download_progressbar.set(0)
        self.download_progressbar.grid_remove()

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
            self.settings_page, 
            width=550, 
            height=380,
            corner_radius=10
        )
        self.settings_tabview.grid(row=0, column=0, padx=25, pady=20, sticky="nsew")
        self.settings_tabview.add("路径设置")
        self.settings_tabview.add("更新")
        self.settings_tabview.add("按钮显示")
        self.settings_tabview.add("关于")

        # 设置各标签页
        self.setup_settings_path_tab()
        self.setup_settings_update_tab()
        self.setup_settings_buttons_tab()
        self.setup_settings_about_tab()

    def setup_settings_path_tab(self):
        """路径设置标签页"""
        settings_frame = self.settings_tabview.tab("路径设置")
        settings_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            settings_frame, 
            text="游戏路径设置", 
            font=("Microsoft YaHei", 18, "bold"), 
            text_color="#333333"
        ).grid(row=0, column=0, pady=20)

        self.path_display = ctk.CTkEntry(
            settings_frame, 
            width=420, 
            height=38, 
            placeholder_text="请输入或选择游戏根目录",
            corner_radius=10
        )
        self.path_display.grid(row=1, column=0, pady=5, padx=20)
        if self.game_root_path: self.path_display.insert(0, self.game_root_path)

        btn_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=18)
        ctk.CTkButton(
            btn_frame, 
            text="浏览...", 
            width=110, 
            height=35,
            corner_radius=10,
            command=self.browse_folder
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_frame, 
            text="保存路径", 
            width=110, 
            height=35,
            corner_radius=10,
            fg_color="#28a745", 
            hover_color="#218838", 
            command=self.save_manual_path
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            settings_frame, 
            text="提示：检测到 BepInEx/nebula/Nebula.dll 的目录才会显示", 
            text_color="#aaaaaa", 
            font=("Microsoft YaHei", 11)
        ).grid(row=3, column=0, pady=10)

    def setup_settings_update_tab(self):
        """更新标签页"""
        update_frame = self.settings_tabview.tab("更新")
        update_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            update_frame, 
            text="检查更新", 
            font=("Microsoft YaHei", 18, "bold"), 
            text_color="#333333"
        ).grid(row=0, column=0, pady=15)
        
        # 启动器更新按钮
        self.check_update_button = ctk.CTkButton(
            update_frame,
            text="检查启动器更新",
            width=220,
            height=40,
            corner_radius=10,
            font=("Microsoft YaHei", 14),
            fg_color="#5a8ab5",
            hover_color="#4a7a9b",
            command=self.check_update
        )
        self.check_update_button.grid(row=1, column=0, pady=10)

        ctk.CTkLabel(
            update_frame, 
            text=f"当前版本：{self.current_version}", 
            font=("Microsoft YaHei", 12), 
            text_color="#000000"
        ).grid(row=2, column=0, pady=5)
        
        # 分隔线
        ctk.CTkFrame(update_frame, height=2, fg_color="#5a7a8a").grid(row=3, column=0, sticky="ew", padx=50, pady=15)
        
        # NoS DLL 更新区域
        ctk.CTkLabel(
            update_frame, 
            text="更新 NoS", 
            font=("Microsoft YaHei", 16, "bold"), 
            text_color="#333333"
        ).grid(row=4, column=0, pady=10)
        
        # 版本类型选择
        self.nos_version_type = ctk.CTkOptionMenu(
            update_frame,
            values=["release", "snapshot"],
            width=150,
            height=32,
            corner_radius=8,
            font=("Microsoft YaHei", 12)
        )
        self.nos_version_type.grid(row=5, column=0, pady=5)
        self.nos_version_type.set("release")
        
        self.update_nos_button = ctk.CTkButton(
            update_frame,
            text="更新 NoS",
            width=180,
            height=38,
            corner_radius=10,
            font=("Microsoft YaHei", 13),
            fg_color="#28a745",
            hover_color="#218838",
            command=self.check_nos_update
        )
        self.update_nos_button.grid(row=6, column=0, pady=10)

    def setup_settings_buttons_tab(self):
        """按钮显示标签页"""
        buttons_frame = self.settings_tabview.tab("按钮显示")
        buttons_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            buttons_frame, 
            text="主界面按钮显示设置", 
            font=("Microsoft YaHei", 18, "bold"), 
            text_color="#333333"
        ).grid(row=0, column=0, pady=20)
        
        ctk.CTkLabel(
            buttons_frame, 
            text="选择要在启动页面上显示的按钮：", 
            font=("Microsoft YaHei", 12), 
            text_color="#000000"
        ).grid(row=1, column=0, pady=(5, 15))

        self.addons_checkbox = ctk.CTkCheckBox(
            buttons_frame,
            text="打开插件文件夹",
            font=("Microsoft YaHei", 13),
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=5,
            onvalue=True,
            offvalue=False,
            command=self.on_button_visibility_change
        )
        self.addons_checkbox.grid(row=2, column=0, pady=10)
        self.addons_checkbox.select() if self.button_visibility["addons"] else self.addons_checkbox.deselect()

        self.presets_checkbox = ctk.CTkCheckBox(
            buttons_frame,
            text="打开预设文件夹",
            font=("Microsoft YaHei", 13),
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=5,
            onvalue=True,
            offvalue=False,
            command=self.on_button_visibility_change
        )
        self.presets_checkbox.grid(row=3, column=0, pady=10)
        self.presets_checkbox.select() if self.button_visibility["presets"] else self.presets_checkbox.deselect()

        ctk.CTkLabel(
            buttons_frame, 
            text="更改后立即生效，设置会自动保存", 
            text_color="#aaaaaa", 
            font=("Microsoft YaHei", 11)
        ).grid(row=4, column=0, pady=20)

    def setup_settings_about_tab(self):
        """关于标签页"""
        about_frame = self.settings_tabview.tab("关于")
        about_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            about_frame, 
            text="关于 NoS Launcher", 
            font=("Microsoft YaHei", 18, "bold"), 
            text_color="#333333"
        ).grid(row=0, column=0, pady=20)
        
        ctk.CTkLabel(
            about_frame, 
            text="绿林Greenwoo制作", 
            font=("Microsoft YaHei", 15, "bold"), 
            text_color="#333333"
        ).grid(row=1, column=0, pady=10)
        
        link_label = ctk.CTkLabel(
            about_frame, 
            text="GitHub项目链接", 
            font=("Microsoft YaHei", 13),
            text_color="#5a8ab5",
            cursor="hand2"
        )
        link_label.grid(row=2, column=0, pady=10)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/MHW-YTT/NOS_Launcher"))

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
                light_image=pil_image,
                dark_image=pil_image,
                size=(new_width, new_height)
            )
            
            self.logo_label = ctk.CTkLabel(
                master=self.logo_frame,
                image=logo_image,
                text=""
            )
            self.logo_label.grid(row=0, column=0, pady=5)
            self.logo_image = logo_image
            
        except Exception as e:
            print(f"从网络加载 Logo 失败: {e}")
            self.show_text_logo("NoS Launcher")

    def show_text_logo(self, text):
        self.logo_label = ctk.CTkLabel(
            master=self.logo_frame,
            text=text,
            font=("Microsoft YaHei", 28, "bold"),
            text_color="#ffffff"
        )
        self.logo_label.grid(row=0, column=0, pady=5)

    # ========================================================
    # 配置加载/保存
    # ========================================================
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.game_root_path = config.get("game_path", "")
                    saved_visibility = config.get("button_visibility", {})
                    self.button_visibility["addons"] = saved_visibility.get("addons", True)
                    self.button_visibility["presets"] = saved_visibility.get("presets", True)
                    self.addon_versions = config.get("addon_versions", {})
                if self.game_root_path and os.path.isdir(self.game_root_path):
                    self.scan_game_versions(show_msg=False)
            except:
                pass

    def save_config(self):
        try:
            config = {
                "game_path": self.game_root_path,
                "button_visibility": self.button_visibility,
                "addon_versions": self.addon_versions
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            # 设置为隐藏文件
            try:
                os.system(f'attrib +h "{self.config_file}"')
            except:
                pass
        except:
            pass

    # ========================================================
    # MD5 计算
    # ========================================================
    def calculate_md5(self, file_path):
        """计算文件的MD5值"""
        md5_hash = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            return None

    # ========================================================
    # NoS DLL 更新功能
    # ========================================================
    def check_nos_update(self):
        """检查NoS DLL更新"""
        selected_version = self.version_combobox.get()
        
        if not self.game_root_path or selected_version in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return
        
        version_type = self.nos_version_type.get()
        
        # 获取本地DLL路径
        local_dll_path = os.path.join(self.game_root_path, selected_version, "BepInEx", "nebula", "Nebula.dll")
        
        if not os.path.exists(local_dll_path):
            messagebox.showerror("错误", "未找到 Nebula.dll 文件！")
            return
        
        # 计算本地MD5
        local_md5 = self.calculate_md5(local_dll_path)
        
        # 获取云端版本信息
        try:
            response = requests.get("https://auojplay.fanchuanovo.cn/NoS_Launcher/nos_dll/ver.json", timeout=10)
            response.raise_for_status()
            ver_data = response.json()
            
            # 获取对应类型的版本信息
            type_data = ver_data.get(version_type, {})
            cloud_md5 = type_data.get("md5", "")
            download_url = type_data.get("url", "")
            version_name = type_data.get("ver", "未知")
            
            if not cloud_md5 or not download_url:
                messagebox.showerror("错误", "无法获取云端版本信息！")
                return
            
            if local_md5 == cloud_md5:
                messagebox.showinfo("提示", f"NoS 已是最新版本！\n版本类型: {version_type}\n版本号: {version_name}")
            else:
                result = messagebox.askyesno(
                    "发现新版本", 
                    f"检测到新版本！\n\n版本类型: {version_type}\n版本号: {version_name}\n\n是否立即更新？"
                )
                if result:
                    self.download_nos_dll(download_url, local_dll_path, version_type, version_name)
                    
        except Exception as e:
            messagebox.showerror("错误", f"检查更新失败：{e}")

    def download_nos_dll(self, url, save_path, version_type, version_name):
        """下载NoS DLL"""
        download_window = DownloadWindow(self, f"更新 NoS ({version_type})")
        download_window.log(f"版本类型: {version_type}")
        download_window.log(f"版本号: {version_name}")
        download_window.log(f"下载地址: {url}")
        download_window.log(f"保存路径: {save_path}")
        download_window.log("-" * 50)
        download_window.set_status("正在连接服务器...")
        
        def download_thread():
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                download_window.log(f"文件大小: {total_size / 1024:.2f} KB")
                download_window.log("开始下载...")
                
                # 先下载到临时文件
                temp_path = save_path + ".tmp"
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = downloaded / total_size
                                download_window.after(0, lambda p=progress: download_window.set_progress(p))
                                download_window.after(0, lambda d=downloaded, t=total_size: 
                                    download_window.set_status(f"下载中... {d}/{t} bytes"))
                
                download_window.log("下载完成，正在替换文件...")
                
                # 替换原文件
                if os.path.exists(save_path):
                    os.remove(save_path)
                os.rename(temp_path, save_path)
                
                download_window.log("文件替换成功！")
                download_window.log("-" * 50)
                download_window.set_status("更新完成！")
                download_window.set_progress(1)
                download_window.after(0, lambda: download_window.show_close_button())
                download_window.after(0, lambda: messagebox.showinfo("成功", "NoS 更新成功！"))
                
            except Exception as e:
                download_window.log(f"下载失败: {e}")
                download_window.set_status(f"下载失败: {e}")
                download_window.after(0, lambda: download_window.show_close_button())
        
        threading.Thread(target=download_thread, daemon=True).start()

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
            self.addon_list_frame, 
            text="正在加载插件列表...", 
            font=("Microsoft YaHei", 12),
            text_color="#888888"
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
                self.addon_list_frame, 
                text="暂无可用插件", 
                font=("Microsoft YaHei", 12),
                text_color="#888888"
            ).grid(row=0, column=0, pady=20)
            return

        self.addon_data = addon_data
        
        selected_version = self.version_combobox.get()
        addons_path = None
        if self.game_root_path and selected_version not in ["请先在设置中添加文件夹", "未找到有效版本"]:
            addons_path = os.path.join(self.game_root_path, selected_version, "Addons")

        for idx, (name, info) in enumerate(addon_data.items()):
            # 兼容旧格式和新格式
            if isinstance(info, dict):
                url = info.get("url", "")
                cloud_version = info.get("ver", "")
            else:
                url = info
                cloud_version = ""
            
            filename = url.split("/")[-1]
            if not filename or not filename.lower().endswith('.zip'):
                filename = f"{name}.zip"
            
            is_installed = False
            need_update = False
            if addons_path and os.path.isdir(addons_path):
                plugin_file = os.path.join(addons_path, filename)
                is_installed = os.path.exists(plugin_file)
                
                # 检查是否需要更新
                if is_installed and cloud_version:
                    local_version = self.addon_versions.get(name, "")
                    need_update = local_version != cloud_version
            
            addon_item = ctk.CTkFrame(
                self.addon_list_frame, 
                fg_color="#5a7a8a", 
                corner_radius=10,
                height=50
            )
            addon_item.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            addon_item.grid_columnconfigure(0, weight=1)
            addon_item.grid_propagate(False)

            # 显示名称和版本
            display_text = name
            if cloud_version:
                display_text = f"{name} (v{cloud_version})"
            
            name_label = ctk.CTkLabel(
                addon_item, 
                text=display_text, 
                font=("Microsoft YaHei", 13),
                anchor="w",
                text_color="#ffffff"
            )
            name_label.grid(row=0, column=0, padx=18, pady=12, sticky="w")

            if need_update:
                download_btn = ctk.CTkButton(
                    addon_item,
                    text="更新",
                    width=65,
                    height=30,
                    corner_radius=8,
                    font=("Microsoft YaHei", 12),
                    fg_color="#ffc107",
                    hover_color="#e0a800",
                    text_color="#000000",
                    command=lambda n=name, u=url, v=cloud_version: self.download_addon_with_version(n, u, v)
                )
            elif is_installed:
                download_btn = ctk.CTkButton(
                    addon_item,
                    text="已安装",
                    width=75,
                    height=30,
                    corner_radius=8,
                    font=("Microsoft YaHei", 12),
                    fg_color="#6c757d",
                    hover_color="#5a6268",
                    command=lambda n=name, u=url, v=cloud_version: self.download_addon_with_version(n, u, v)
                )
            else:
                download_btn = ctk.CTkButton(
                    addon_item,
                    text="下载",
                    width=65,
                    height=30,
                    corner_radius=8,
                    font=("Microsoft YaHei", 12),
                    fg_color="#28a745",
                    hover_color="#218838",
                    command=lambda n=name, u=url, v=cloud_version: self.download_addon_with_version(n, u, v)
                )
            download_btn.grid(row=0, column=1, padx=12, pady=10)

    def _show_addon_list_error(self, error_msg):
        if not hasattr(self, 'addon_list_frame'):
            return
            
        for widget in self.addon_list_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.addon_list_frame, 
            text=f"加载失败：{error_msg}", 
            font=("Microsoft YaHei", 11),
            text_color="#ff6b6b"
        ).grid(row=0, column=0, pady=20)

        retry_btn = ctk.CTkButton(
            self.addon_list_frame,
            text="重试",
            width=80,
            height=30,
            corner_radius=10,
            font=("Microsoft YaHei", 12),
            command=self.load_addon_list
        )
        retry_btn.grid(row=1, column=0, pady=10)

    def download_addon_with_version(self, addon_name, addon_url, cloud_version=""):
        """带版本号的插件下载"""
        selected_version = self.version_combobox.get()
        
        if not self.game_root_path or selected_version in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return
        
        # 检查是否已是最新版本
        if cloud_version:
            local_version = self.addon_versions.get(addon_name, "")
            if local_version == cloud_version:
                result = messagebox.askyesno(
                    "提示", 
                    f"插件 {addon_name} 已是最新版本 (v{cloud_version})\n\n是否重新下载？"
                )
                if not result:
                    return
        
        # 创建下载窗口
        download_window = DownloadWindow(self, f"下载插件 - {addon_name}")
        download_window.log(f"插件名称: {addon_name}")
        if cloud_version:
            download_window.log(f"版本号: {cloud_version}")
        download_window.log(f"下载地址: {addon_url}")
        download_window.log("-" * 50)
        download_window.set_status("正在连接服务器...")
        
        def download_thread():
            try:
                addons_path = os.path.join(self.game_root_path, selected_version, "Addons")
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
                                download_window.after(0, lambda d=downloaded, t=total_size: 
                                    download_window.set_status(f"下载中... {d}/{t} bytes"))

                download_window.log("下载完成！")
                
                # 保存版本信息
                if cloud_version:
                    self.addon_versions[addon_name] = cloud_version
                    self.save_config()
                    download_window.log(f"已记录版本: v{cloud_version}")
                
                download_window.log("-" * 50)
                download_window.set_status("下载完成！")
                download_window.set_progress(1)
                download_window.after(0, lambda: download_window.show_close_button())
                download_window.after(0, lambda: messagebox.showinfo("成功", f"插件 {addon_name} 下载成功！"))
                
                # 刷新插件列表
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
        if self.current_versions:
            if self.button_visibility["addons"]:
                self.addons_button.grid()
            else:
                self.addons_button.grid_remove()
                
            if self.button_visibility["presets"]:
                self.presets_button.grid()
            else:
                self.presets_button.grid_remove()

    def browse_folder(self):
        selected_path = filedialog.askdirectory(title="选择游戏根目录")
        if selected_path:
            self.path_display.delete(0, "end")
            self.path_display.insert(0, selected_path)
            self.apply_path_change(selected_path)

    def save_manual_path(self):
        path = self.path_display.get().strip()
        if path: 
            self.apply_path_change(path)
        else: 
            messagebox.showwarning("提示", "路径不能为空！")

    def apply_path_change(self, path):
        if not os.path.isdir(path):
            messagebox.showerror("错误", "路径无效或不是一个文件夹。")
            return
        self.game_root_path = path
        self.save_config()
        self.scan_game_versions(show_msg=True)

    def scan_game_versions(self, show_msg=True):
        if not hasattr(self, 'version_combobox') or not self.version_combobox:
            return

        if not os.path.isdir(self.game_root_path):
            return

        try:
            all_items = os.listdir(self.game_root_path)
            versions = []
            
            for item in all_items:
                full_path = os.path.join(self.game_root_path, item)
                if os.path.isdir(full_path):
                    nebula_dll_path = os.path.join(full_path, "BepInEx", "nebula", "Nebula.dll")
                    if os.path.exists(nebula_dll_path):
                        versions.append(item)

            if versions:
                self.current_versions = sorted(versions)
                self.version_combobox.configure(values=self.current_versions)
                self.version_combobox.set(self.current_versions[0])
                self.update_main_buttons_visibility()
                if show_msg:
                    messagebox.showinfo("成功", f"扫描完成，找到 {len(versions)} 个有效游戏版本。")
            else:
                self.current_versions = []
                self.version_combobox.configure(values=["未找到有效版本"])
                self.version_combobox.set("未找到有效版本")
                self.addons_button.grid_remove()
                self.presets_button.grid_remove()
                if show_msg:
                    messagebox.showwarning("警告", "未找到包含完整文件的游戏版本。")

        except Exception as e:
            messagebox.showerror("错误", f"扫描文件夹时出错：{e}")

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
        selected_version = self.version_combobox.get()
        
        if not self.game_root_path or selected_version in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先在设置中添加有效的游戏文件夹！")
            return
            
        if not self.is_steam_running():
            steam_exe = self.get_steam_path()
            if steam_exe and os.path.exists(steam_exe):
                try:
                    subprocess.Popen(steam_exe)
                    messagebox.showinfo("提示", "检测到 Steam 未运行。\n正在为你启动 Steam，请稍后重试。")
                    return
                except: pass
            messagebox.showwarning("提示", "请先启动 Steam 后再运行游戏。")
            return

        game_dir = os.path.join(self.game_root_path, selected_version)
        exe_path = os.path.join(game_dir, "Among Us.exe")
        
        if not os.path.exists(exe_path):
            messagebox.showerror("错误", f"未找到游戏程序：\n{exe_path}")
            return

        try:
            subprocess.Popen(exe_path, cwd=game_dir)
        except Exception as e:
            messagebox.showerror("启动失败", f"启动游戏时发生错误：\n{e}")

    def open_addons_folder(self):
        selected_version = self.version_combobox.get()
        if not self.game_root_path or selected_version in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return
            
        addons_path = os.path.join(self.game_root_path, selected_version, "Addons")
        if os.path.isdir(addons_path):
            try:
                os.startfile(addons_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：\n{e}")
        else:
            messagebox.showwarning("提示", f"插件文件夹不存在：\n{addons_path}")

    def open_presets_folder(self):
        selected_version = self.version_combobox.get()
        if not self.game_root_path or selected_version in ["请先在设置中添加文件夹", "未找到有效版本"]:
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return
            
        presets_path = os.path.join(self.game_root_path, selected_version, "Presets")
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

if __name__ == "__main__":
    app = NOSLauncher()
    app.mainloop()
