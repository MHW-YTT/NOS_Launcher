import customtkinter as ctk
import os
import json
import subprocess
import winreg
from PIL import Image
from tkinter import filedialog, messagebox
import webbrowser
import requests
from io import BytesIO
import threading

# 设置外观模式和颜色主题
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class NOSLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 配置窗口
        self.title("NoS Launcher")
        self.geometry("600x550") 
        self.minsize(500, 450)
        
        self.configure(fg_color="#426666")
        self.eval('tk::PlaceWindow . center')

        # 数据存储
        self.game_root_path = "" 
        self.current_versions = []
        self.config_file = "config.json"
        self.current_version = "1.0.0"  # 当前启动器版本
        
        # 按钮显示配置（默认都显示）
        self.button_visibility = {
            "addons": True,    # 插件文件夹按钮
            "presets": True    # 预设文件夹按钮
        }

        # 创建主容器
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # -------------------------------------------------------
        # 顶部 Logo 区域
        # -------------------------------------------------------
        self.logo_frame = ctk.CTkFrame(master=self, fg_color="#426666", corner_radius=0)
        self.logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))
        self.logo_frame.grid_columnconfigure(0, weight=1)

        self.load_logo()

        # -------------------------------------------------------
        # 主体内容区域
        # -------------------------------------------------------
        self.main_frame = ctk.CTkFrame(master=self, corner_radius=20, border_width=2, border_color="#d0d0d0", fg_color="#425466")
        self.main_frame.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="nsew")
        
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure((0,1,2,3,4,5,6), weight=1)

        # 1. 标题
        self.label_title = ctk.CTkLabel(master=self.main_frame, text="欢迎使用 NoS Launcher", font=("Microsoft YaHei", 20, "bold"), text_color="#ffffff")
        self.label_title.grid(row=0, column=0, pady=(30, 10))

        # 2. 版本选择区域
        self.version_label = ctk.CTkLabel(master=self.main_frame, text="当前游戏版本：", font=("Microsoft YaHei", 14), text_color="#ffffff")
        self.version_label.grid(row=1, column=0, pady=(5, 5))

        self.version_combobox = ctk.CTkOptionMenu(master=self.main_frame, values=["请先在设置中添加文件夹"], width=250, height=35, corner_radius=10, font=("Microsoft YaHei", 13), dynamic_resizing=False)
        self.version_combobox.grid(row=2, column=0, pady=(0, 15))

        # 3. 启动按钮
        self.launch_button = ctk.CTkButton(
            master=self.main_frame, 
            text="启动游戏", 
            width=250, 
            height=45, 
            corner_radius=20, 
            font=("Microsoft YaHei", 16, "bold"), 
            command=self.launch_game,
            fg_color="#5a8ab5",
            hover_color="#4a7a9b"
        )
        self.launch_button.grid(row=3, column=0, pady=10)

        # 4. 打开插件文件夹按钮 (位置调整至启动按钮下方)
        self.addons_button = ctk.CTkButton(
            master=self.main_frame,
            text="打开插件文件夹",
            width=250,
            height=35,
            corner_radius=15,
            font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5",
            hover_color="#4a7a9b",
            command=self.open_addons_folder
        )
        # 初始隐藏，扫描成功后显示
        self.addons_button.grid(row=4, column=0, pady=10)
        self.addons_button.grid_remove() 

        # 5. 打开预设文件夹按钮 (位置调整至插件按钮下方)
        self.presets_button = ctk.CTkButton(
            master=self.main_frame,
            text="打开预设文件夹",
            width=250,
            height=35,
            corner_radius=15,
            font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5",
            hover_color="#4a7a9b",
            command=self.open_presets_folder
        )
        # 初始隐藏，扫描成功后显示
        self.presets_button.grid(row=5, column=0, pady=10)
        self.presets_button.grid_remove()

        # 6. 设置按钮 (行号调整)
        self.settings_button = ctk.CTkButton(
            master=self.main_frame,
            text="设置",
            width=150,
            height=35,
            corner_radius=15,
            font=("Microsoft YaHei", 13),
            fg_color="#5a6b7a",
            hover_color="#4a5b6a",
            command=self.open_settings
        )
        self.settings_button.grid(row=6, column=0, pady=10)

        # 7. 版本号 (行号调整)
        self.version_label_bottom = ctk.CTkLabel(
            master=self.main_frame,
            text=f"NoS Launcher {self.current_version}",
            font=("Microsoft YaHei", 10),
            text_color="#aaaaaa"
        )
        self.version_label_bottom.grid(row=7, column=0, pady=(10, 20))

        # 在所有UI元素创建后，再加载配置
        self.load_config()
        
        # 启动时自动检测更新
        self.after(1000, self.check_update_on_startup)  # 延迟1秒后检测，避免阻塞启动

    def load_logo(self):
        try:
            # 网络图片URL
            logo_url = "https://ytt0.top/NOS_Launcher/re/nos.png"
            
            # 发送GET请求获取图片
            response = requests.get(logo_url, timeout=5)
            response.raise_for_status()  # 检查请求是否成功（如404、500等错误）
            
            # 将响应内容转换为PIL Image对象
            pil_image = Image.open(BytesIO(response.content))
            
            # 缩放处理
            max_width = 400
            original_width, original_height = pil_image.size
            
            if original_width > max_width:
                scale_ratio = max_width / original_width
                new_height = int(original_height * scale_ratio)
                new_width = max_width
            else:
                new_width = original_width
                new_height = original_height
            
            # 创建CTkImage
            logo_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(new_width, new_height)
            )
            
            # 显示Logo
            self.logo_label = ctk.CTkLabel(
                master=self.logo_frame,
                image=logo_image,
                text=""
            )
            self.logo_label.grid(row=0, column=0, pady=20)
            self.logo_image = logo_image
            
        except requests.exceptions.RequestException as e:
            # 网络请求失败（如超时、404等）
            print(f"从网络加载 Logo 失败: {e}")
            self.show_text_logo("NoS Launcher")
        except Exception as e:
            # 其他错误（如图片格式错误）
            print(f"处理 Logo 时出错: {e}")
            self.show_text_logo("NoS Launcher")

    def show_text_logo(self, text):
        self.logo_label = ctk.CTkLabel(
            master=self.logo_frame,
            text=text,
            font=("Microsoft YaHei", 32, "bold"),
            text_color="#ffffff"
        )
        self.logo_label.grid(row=0, column=0, pady=20)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.game_root_path = config.get("game_path", "")
                    # 加载按钮显示配置
                    saved_visibility = config.get("button_visibility", {})
                    self.button_visibility["addons"] = saved_visibility.get("addons", True)
                    self.button_visibility["presets"] = saved_visibility.get("presets", True)
                if self.game_root_path and os.path.isdir(self.game_root_path):
                    self.scan_game_versions(show_msg=False)
            except:
                pass

    def save_config(self):
        try:
            config = {
                "game_path": self.game_root_path,
                "button_visibility": self.button_visibility
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except:
            pass

    def open_settings(self):
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("设置")
        self.settings_window.geometry("500x350")
        self.settings_window.resizable(False, False)
        # 使用 transient 让设置窗口保持在主窗口上方，但不置顶于所有窗口
        self.settings_window.transient(self)
        # 让设置窗口获得焦点
        self.settings_window.focus_force()
        # 抓取焦点，防止用户操作主窗口
        self.settings_window.grab_set()
        
        self.update_idletasks()
        x = int(self.winfo_x() + (self.winfo_width()/2) - 250)
        y = int(self.winfo_y() + (self.winfo_height()/2) - 175)
        self.settings_window.geometry(f"500x350+{x}+{y}")

        # 使用选项卡 - 调整顺序：设置、更新、按钮选择、插件市场、关于
        self.tabview = ctk.CTkTabview(self.settings_window, width=460, height=280)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.tabview.add("设置")
        self.tabview.add("更新")
        self.tabview.add("按钮选择")
        self.tabview.add("插件市场")  # 插件市场
        self.tabview.add("关于")  # 关于调整到最后

        # 设置标签页
        self.setup_settings_tab()
        # 更新标签页
        self.setup_update_tab()
        # 按钮选择标签页
        self.setup_buttons_tab()
        # 插件市场标签页
        self.setup_addon_market_tab()
        # 关于标签页（放最后）
        self.setup_about_tab()

    def setup_settings_tab(self):
        settings_frame = self.tabview.tab("设置")
        settings_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(settings_frame, text="启动器设置", font=("Microsoft YaHei", 18, "bold")).grid(row=0, column=0, pady=20)

        self.path_display = ctk.CTkEntry(settings_frame, width=400, height=35, placeholder_text="请输入或选择游戏根目录")
        self.path_display.grid(row=1, column=0, pady=5, padx=20)
        if self.game_root_path: self.path_display.insert(0, self.game_root_path)

        btn_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=15)
        ctk.CTkButton(btn_frame, text="浏览...", width=100, command=self.browse_folder).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="保存路径", width=100, fg_color="#28a745", hover_color="#218838", command=self.save_manual_path).pack(side="left", padx=10)

        ctk.CTkLabel(settings_frame, text="只有包含完整文件的版本(运行过exe后)才会显示在列表中", text_color="gray", font=("Microsoft YaHei", 11)).grid(row=3, column=0, pady=10)

    def setup_addon_market_tab(self):
        """插件市场标签页"""
        self.addon_market_frame = self.tabview.tab("插件市场")
        self.addon_market_frame.grid_columnconfigure(0, weight=1)
        self.addon_market_frame.grid_rowconfigure(1, weight=1)

        # 标题
        ctk.CTkLabel(self.addon_market_frame, text="插件市场", font=("Microsoft YaHei", 18, "bold")).grid(row=0, column=0, pady=(15, 10))

        # 插件列表容器（使用 ScrollableFrame）
        self.addon_list_frame = ctk.CTkScrollableFrame(self.addon_market_frame, width=420, height=180)
        self.addon_list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.addon_list_frame.grid_columnconfigure(0, weight=1)

        # 进度条区域
        self.download_progress_frame = ctk.CTkFrame(self.addon_market_frame, fg_color="transparent")
        self.download_progress_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.download_progress_frame.grid_columnconfigure(0, weight=1)

        # 下载状态标签
        self.download_status_label = ctk.CTkLabel(
            self.download_progress_frame, 
            text="", 
            font=("Microsoft YaHei", 11),
            text_color="#aaaaaa"
        )
        self.download_status_label.grid(row=0, column=0, pady=(0, 2))

        # 进度条
        self.download_progressbar = ctk.CTkProgressBar(
            self.download_progress_frame,
            width=400,
            height=15,
            corner_radius=5
        )
        self.download_progressbar.grid(row=1, column=0, pady=2)
        self.download_progressbar.set(0)
        self.download_progressbar.grid_remove()  # 初始隐藏

        # 加载插件列表
        self.load_addon_list()

    def load_addon_list(self):
        """加载插件列表"""
        print("[加载插件列表] 开始...")
        
        # 清空现有列表
        for widget in self.addon_list_frame.winfo_children():
            widget.destroy()

        # 显示加载中
        loading_label = ctk.CTkLabel(
            self.addon_list_frame, 
            text="正在加载插件列表...", 
            font=("Microsoft YaHei", 12),
            text_color="#888888"
        )
        loading_label.grid(row=0, column=0, pady=20)

        # 在后台线程加载
        print("[加载插件列表] 启动后台线程...")
        threading.Thread(target=self._fetch_addon_list, daemon=True).start()

    def _fetch_addon_list(self):
        """后台获取插件列表"""
        print("[获取插件列表] 开始获取...")
        try:
            response = requests.get("https://ytt0.top/NOS_Launcher/addons/list.json", timeout=10)
            response.raise_for_status()
            addon_data = response.json()
            print(f"[获取插件列表] 获取成功，共 {len(addon_data)} 个插件")
            
            # 在主线程更新UI
            self.after(0, lambda: self._display_addon_list(addon_data))
        except Exception as e:
            error_msg = str(e)  # 立即捕获错误信息
            print(f"[获取插件列表] 获取失败: {error_msg}")
            self.after(0, lambda: self._show_addon_list_error(error_msg))

    def _display_addon_list(self, addon_data):
        """显示插件列表"""
        print(f"[显示插件列表] 开始显示，数据: {addon_data}")
        
        # 检查控件是否存在
        if not self._check_addon_widgets():
            print("[显示插件列表] 控件检查失败，跳过显示")
            return
            
        # 清空现有列表
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

        # 存储插件数据
        self.addon_data = addon_data
        
        # 获取当前选中版本的 Addons 路径
        selected_version = self.version_combobox.get()
        addons_path = None
        if self.game_root_path and selected_version not in ["请先在设置中添加文件夹", "未找到有效版本"]:
            addons_path = os.path.join(self.game_root_path, selected_version, "Addons")
            print(f"[显示插件列表] Addons路径: {addons_path}")

        # 显示每个插件
        for idx, (name, url) in enumerate(addon_data.items()):
            print(f"[显示插件列表] 添加插件项: {name} -> {url}")
            
            # 从URL获取文件名
            filename = url.split("/")[-1]
            if not filename or not filename.lower().endswith('.zip'):
                filename = f"{name}.zip"
            
            # 检查是否已安装
            is_installed = False
            if addons_path and os.path.isdir(addons_path):
                plugin_file = os.path.join(addons_path, filename)
                is_installed = os.path.exists(plugin_file)
                print(f"[显示插件列表] 检查文件 {plugin_file}: {'存在' if is_installed else '不存在'}")
            
            addon_item = ctk.CTkFrame(
                self.addon_list_frame, 
                fg_color="#b2c4ce", 
                corner_radius=10,
                height=40
            )
            addon_item.grid(row=idx, column=0, padx=5, pady=3, sticky="ew")
            addon_item.grid_columnconfigure(0, weight=1)
            addon_item.grid_propagate(False)

            # 插件名称
            name_label = ctk.CTkLabel(
                addon_item, 
                text=name, 
                font=("Microsoft YaHei", 12),
                anchor="w"
            )
            name_label.grid(row=0, column=0, padx=15, pady=8, sticky="w")

            # 下载按钮 - 根据安装状态显示不同文字和颜色
            if is_installed:
                download_btn = ctk.CTkButton(
                    addon_item,
                    text="已安装",
                    width=70,
                    height=26,
                    corner_radius=8,
                    font=("Microsoft YaHei", 11),
                    fg_color="#6c757d",
                    hover_color="#5a6268",
                    command=lambda n=name, u=url: self.download_addon(n, u)
                )
            else:
                download_btn = ctk.CTkButton(
                    addon_item,
                    text="下载",
                    width=60,
                    height=26,
                    corner_radius=8,
                    font=("Microsoft YaHei", 11),
                    fg_color="#28a745",
                    hover_color="#218838",
                    command=lambda n=name, u=url: self.download_addon(n, u)
                )
            download_btn.grid(row=0, column=1, padx=10, pady=7)
        
        print("[显示插件列表] 显示完成")

    def _show_addon_list_error(self, error_msg):
        """显示插件列表加载错误"""
        print(f"[显示错误] 错误信息: {error_msg}")
        
        # 检查控件是否存在
        if not self._check_addon_widgets():
            print("[显示错误] 控件检查失败，跳过显示")
            return
            
        for widget in self.addon_list_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.addon_list_frame, 
            text=f"加载失败：{error_msg}", 
            font=("Microsoft YaHei", 11),
            text_color="#ff6b6b"
        ).grid(row=0, column=0, pady=20)

        # 重试按钮
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
        print("[显示错误] 错误界面显示完成")

    def _check_addon_widgets(self):
        """检查插件市场相关控件是否存在"""
        try:
            # 检查窗口是否存在
            if not hasattr(self, 'settings_window'):
                print("[检查控件] settings_window 属性不存在")
                return False
            if not self.settings_window.winfo_exists():
                print("[检查控件] settings_window 窗口不存在")
                return False
            # 检查列表框架是否存在
            if not hasattr(self, 'addon_list_frame'):
                print("[检查控件] addon_list_frame 属性不存在")
                return False
            if not self.addon_list_frame.winfo_exists():
                print("[检查控件] addon_list_frame 窗口不存在")
                return False
            print("[检查控件] 所有控件存在")
            return True
        except Exception as e:
            print(f"[检查控件] 异常: {e}")
            return False

    def download_addon(self, addon_name, addon_url):
        """下载插件"""
        print(f"[下载] 开始下载插件: {addon_name}, URL: {addon_url}")
        
        # 检查是否选择了游戏版本
        selected_version = self.version_combobox.get()
        print(f"[下载] 选中的游戏版本: {selected_version}")
        print(f"[下载] 游戏根路径: {self.game_root_path}")
        
        if not self.game_root_path or selected_version == "请先在设置中添加文件夹" or selected_version == "未找到有效版本":
            print("[下载] 错误: 未选择有效的游戏版本")
            messagebox.showwarning("提示", "请先在主界面选择有效的游戏版本！")
            return

        # 检查控件是否存在
        if not self._check_addon_widgets():
            print("[下载] 错误: 控件不存在")
            return

        # 显示进度条
        try:
            print("[下载] 显示进度条...")
            self.download_progressbar.grid()
            self.download_progressbar.set(0)
            self.download_status_label.configure(text=f"正在下载：{addon_name}...")
            print("[下载] 进度条显示成功")
        except Exception as e:
            print(f"[下载] 显示进度条失败: {e}")
            return

        # 在后台线程下载
        print(f"[下载] 启动后台下载线程...")
        threading.Thread(
            target=self._download_addon_thread, 
            args=(addon_name, addon_url, selected_version),
            daemon=True
        ).start()

    def _download_addon_thread(self, addon_name, addon_url, selected_version):
        """后台下载插件线程"""
        print(f"[下载线程] 开始下载: {addon_name}")
        try:
            # 获取目标路径
            addons_path = os.path.join(self.game_root_path, selected_version, "Addons")
            print(f"[下载线程] 目标路径: {addons_path}")
            
            if not os.path.isdir(addons_path):
                print(f"[下载线程] 创建目录: {addons_path}")
                os.makedirs(addons_path)

            # 从URL获取文件名
            filename = addon_url.split("/")[-1]
            print(f"[下载线程] URL文件名: {filename}")
            
            if not filename or not filename.lower().endswith('.zip'):
                filename = f"{addon_name}.zip"
                print(f"[下载线程] 使用默认文件名: {filename}")
            
            # 下载文件
            print(f"[下载线程] 开始请求URL: {addon_url}")
            response = requests.get(addon_url, stream=True, timeout=30)
            response.raise_for_status()
            print(f"[下载线程] HTTP响应状态码: {response.status_code}")

            total_size = int(response.headers.get('content-length', 0))
            print(f"[下载线程] 文件总大小: {total_size} bytes")
            downloaded = 0

            # 最终文件路径
            final_path = os.path.join(addons_path, filename)
            print(f"[下载线程] 最终保存路径: {final_path}")

            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size
                            self.after(0, lambda p=progress: self._safe_set_progress(p))

            print(f"[下载线程] 下载完成，共下载 {downloaded} bytes")

            # 下载完成
            print("[下载线程] 调用下载完成回调")
            self.after(0, lambda: self._download_complete(addon_name))

        except Exception as e:
            error_msg = str(e)
            print(f"[下载线程] 下载出错: {error_msg}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda: self._download_error(error_msg))

    def _safe_set_progress(self, progress):
        """安全设置进度条"""
        try:
            if self._check_addon_widgets() and hasattr(self, 'download_progressbar'):
                self.download_progressbar.set(progress)
                print(f"[进度] {progress*100:.1f}%")
        except Exception as e:
            print(f"[进度] 设置进度失败: {e}")

    def _download_complete(self, addon_name):
        """下载完成回调"""
        print(f"[下载完成] {addon_name}")
        try:
            if self._check_addon_widgets():
                self.download_progressbar.set(1)
                self.download_status_label.configure(text=f"✓ {addon_name} 下载完成！", text_color="#28a745")
                print("[下载完成] UI更新成功")
                
                # 显示下载成功提示窗口
                messagebox.showinfo("下载完成", f"插件 {addon_name} 下载成功！\n已保存到 Addons 文件夹。")
                
                # 2秒后隐藏进度条
                self.after(2000, self._hide_progress)
            else:
                print("[下载完成] 控件不存在，跳过UI更新")
        except Exception as e:
            print(f"[下载完成] UI更新失败: {e}")

    def _download_error(self, error_msg):
        """下载错误回调"""
        print(f"[下载错误] {error_msg}")
        try:
            if self._check_addon_widgets():
                self.download_progressbar.grid_remove()
                self.download_status_label.configure(text=f"下载失败：{error_msg}", text_color="#ff6b6b")
                print("[下载错误] UI更新成功")
            else:
                print("[下载错误] 控件不存在，跳过UI更新")
        except Exception as e:
            print(f"[下载错误] UI更新失败: {e}")

    def _hide_progress(self):
        """隐藏进度条"""
        print("[隐藏进度条]")
        try:
            if self._check_addon_widgets():
                self.download_progressbar.grid_remove()
                self.download_status_label.configure(text="", text_color="#aaaaaa")
                print("[隐藏进度条] 成功")
        except Exception as e:
            print(f"[隐藏进度条] 失败: {e}")

    def setup_about_tab(self):
        about_frame = self.tabview.tab("关于")
        about_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(about_frame, text="关于 NoS Launcher", font=("Microsoft YaHei", 18, "bold")).grid(row=0, column=0, pady=20)
        ctk.CTkLabel(about_frame, text="绿林Greenwoo制作", font=("Microsoft YaHei", 16, "bold")).grid(row=1, column=0, pady=10)
        
        link_label = ctk.CTkLabel(
            about_frame, 
            text="GitHub项目链接", 
            font=("Microsoft YaHei", 14),
            text_color="#5a8ab5",
            cursor="hand2"
        )
        link_label.grid(row=2, column=0, pady=10)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/MHW-YTT/NOS_Launcher"))

    def setup_buttons_tab(self):
        """按钮选择标签页"""
        buttons_frame = self.tabview.tab("按钮选择")
        buttons_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(buttons_frame, text="主界面按钮显示设置", font=("Microsoft YaHei", 18, "bold")).grid(row=0, column=0, pady=20)
        
        # 提示文字
        ctk.CTkLabel(buttons_frame, text="选择要在主界面上显示的按钮：", font=("Microsoft YaHei", 12), text_color="#000000").grid(row=1, column=0, pady=(5, 15))

        # 插件文件夹按钮复选框
        self.addons_checkbox = ctk.CTkCheckBox(
            buttons_frame,
            text="打开插件文件夹",
            font=("Microsoft YaHei", 13),
            checkbox_width=20,
            checkbox_height=20,
            onvalue=True,
            offvalue=False,
            command=self.on_button_visibility_change
        )
        self.addons_checkbox.grid(row=2, column=0, pady=8)
        self.addons_checkbox.select() if self.button_visibility["addons"] else self.addons_checkbox.deselect()

        # 预设文件夹按钮复选框
        self.presets_checkbox = ctk.CTkCheckBox(
            buttons_frame,
            text="打开预设文件夹",
            font=("Microsoft YaHei", 13),
            checkbox_width=20,
            checkbox_height=20,
            onvalue=True,
            offvalue=False,
            command=self.on_button_visibility_change
        )
        self.presets_checkbox.grid(row=3, column=0, pady=8)
        self.presets_checkbox.select() if self.button_visibility["presets"] else self.presets_checkbox.deselect()

        # 说明文字
        ctk.CTkLabel(buttons_frame, text="更改后立即生效，设置会自动保存", text_color="gray", font=("Microsoft YaHei", 11)).grid(row=4, column=0, pady=20)

    def on_button_visibility_change(self):
        """按钮可见性改变时的回调"""
        # 更新配置
        self.button_visibility["addons"] = self.addons_checkbox.get()
        self.button_visibility["presets"] = self.presets_checkbox.get()
        
        # 保存配置
        self.save_config()
        
        # 立即更新主界面按钮显示
        self.update_main_buttons_visibility()

    def update_main_buttons_visibility(self):
        """更新主界面按钮的显示状态"""
        # 只有在有效版本扫描成功后才应用按钮可见性
        if self.current_versions:
            if self.button_visibility["addons"]:
                self.addons_button.grid()
            else:
                self.addons_button.grid_remove()
                
            if self.button_visibility["presets"]:
                self.presets_button.grid()
            else:
                self.presets_button.grid_remove()

    def setup_update_tab(self):
        update_frame = self.tabview.tab("更新")
        update_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(update_frame, text="检查更新", font=("Microsoft YaHei", 18, "bold")).grid(row=0, column=0, pady=20)
        
        # 检查更新按钮
        self.check_update_button = ctk.CTkButton(
            update_frame,
            text="检查更新",
            width=200,
            height=35,
            corner_radius=15,
            font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5",
            hover_color="#4a7a9b",
            command=self.check_update
        )
        self.check_update_button.grid(row=1, column=0, pady=20)

        # 当前版本信息
        ctk.CTkLabel(update_frame, text=f"当前版本：{self.current_version}", font=("Microsoft YaHei", 12), text_color="#000000").grid(row=2, column=0, pady=5)

    def browse_folder(self):
        selected_path = filedialog.askdirectory(title="选择游戏根目录")
        if selected_path:
            self.path_display.delete(0, "end")
            self.path_display.insert(0, selected_path)
            self.apply_path_change(selected_path)

    def save_manual_path(self):
        path = self.path_display.get().strip()
        if path: self.apply_path_change(path)
        else: messagebox.showwarning("提示", "路径不能为空！")

    def apply_path_change(self, path):
        if not os.path.isdir(path):
            messagebox.showerror("错误", "路径无效或不是一个文件夹。")
            return
        self.game_root_path = path
        self.save_config()
        self.scan_game_versions(show_msg=True)
        if self.current_versions: self.settings_window.destroy()

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
                    exe_path = os.path.join(full_path, "Among Us.exe")
                    
                    # 检查 Addons、Presets 文件夹和 NebulaLog.txt 文件
                    addons_path = os.path.join(full_path, "Addons")
                    presets_path = os.path.join(full_path, "Presets")
                    log_path = os.path.join(full_path, "NebulaLog.txt")

                    # 只有当 exe、Addons、Presets、NebulaLog.txt 全部存在时，才视为有效版本
                    if (os.path.exists(exe_path) and 
                        os.path.isdir(addons_path) and 
                        os.path.isdir(presets_path) and 
                        os.path.exists(log_path)):
                        versions.append(item)

            if versions:
                self.current_versions = sorted(versions)
                self.version_combobox.configure(values=self.current_versions)
                self.version_combobox.set(self.current_versions[0])
                # 根据配置显示按钮
                self.update_main_buttons_visibility()
                if show_msg:
                    messagebox.showinfo("成功", f"扫描完成，找到 {len(versions)} 个有效游戏版本。")
            else:
                self.current_versions = []
                self.version_combobox.configure(values=["未找到有效版本"])
                self.version_combobox.set("未找到有效版本")
                # 隐藏按钮
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
        
        if not self.game_root_path or selected_version == "请先在设置中添加文件夹" or selected_version == "未找到有效版本":
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
        """打开插件文件夹"""
        selected_version = self.version_combobox.get()
        if not self.game_root_path or selected_version == "请先在设置中添加文件夹" or selected_version == "未找到有效版本":
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return
            
        addons_path = os.path.join(self.game_root_path, selected_version, "Addons")
        # 使用os.startfile直接打开文件夹（更可靠）
        if os.path.isdir(addons_path):
            try:
                os.startfile(addons_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：\n{e}")
        else:
            messagebox.showwarning("提示", f"插件文件夹不存在：\n{addons_path}")

    def open_presets_folder(self):
        """打开预设文件夹"""
        selected_version = self.version_combobox.get()
        if not self.game_root_path or selected_version == "请先在设置中添加文件夹" or selected_version == "未找到有效版本":
            messagebox.showwarning("提示", "请先选择有效的游戏版本！")
            return
            
        presets_path = os.path.join(self.game_root_path, selected_version, "Presets")
        # 使用os.startfile直接打开文件夹（更可靠）
        if os.path.isdir(presets_path):
            try:
                os.startfile(presets_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：\n{e}")
        else:
            messagebox.showwarning("提示", f"预设文件夹不存在：\n{presets_path}")

    def check_update(self):
        """检查更新"""
        try:
            # 从网络获取更新信息
            response = requests.get("https://ytt0.top/NOS_Launcher/update.json", timeout=5)
            response.raise_for_status()
            update_data = response.json()
            
            # 获取最新版本和下载链接
            latest_version = update_data.get("ver", "")
            download_url = update_data.get("dl", "")
            
            # 比较版本（简单字符串比较，假设版本格式为v1.0.0）
            if latest_version and latest_version > self.current_version:
                # 有新版本，询问是否下载
                result = messagebox.askyesno(
                    "发现新版本", 
                    f"检测到新版本 {latest_version}\n是否立即下载更新？"
                )
                if result:
                    # 打开下载链接
                    webbrowser.open(download_url)
            else:
                messagebox.showinfo("检查更新", "当前已是最新版本")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("检查更新失败", f"无法连接到更新服务器：\n{e}")
        except Exception as e:
            messagebox.showerror("检查更新失败", f"检查更新时出错：\n{e}")

    def check_update_on_startup(self):
        """启动时静默检测更新（只在有新版本时提示）"""
        try:
            # 从网络获取更新信息
            response = requests.get("https://ytt0.top/NOS_Launcher/update.json", timeout=5)
            response.raise_for_status()
            update_data = response.json()
            
            # 获取最新版本和下载链接
            latest_version = update_data.get("ver", "")
            download_url = update_data.get("dl", "")
            
            # 比较版本，只在有新版本时提示
            if latest_version and latest_version > self.current_version:
                # 有新版本，询问是否下载
                result = messagebox.askyesno(
                    "发现新版本", 
                    f"检测到新版本 {latest_version}\n当前版本：{self.current_version}\n\n是否立即下载更新？"
                )
                if result:
                    # 打开下载链接
                    webbrowser.open(download_url)
            # 如果是最新版本，启动时不提示，静默通过
                
        except Exception as e:
            # 启动时检测失败不显示错误，静默处理
            print(f"启动时检查更新失败: {e}")

if __name__ == "__main__":
    app = NOSLauncher()
    app.mainloop()
