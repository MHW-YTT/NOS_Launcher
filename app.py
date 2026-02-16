import customtkinter as ctk
import os
import json
import subprocess
import winreg
from PIL import Image
from tkinter import filedialog, messagebox

# 设置外观模式和颜色主题
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class NOSLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 配置窗口
        self.title("NOS Launcher")
        self.geometry("600x550") 
        self.minsize(500, 450)
        
        self.configure(fg_color="#426666")
        self.eval('tk::PlaceWindow . center')

        # 数据存储
        self.game_root_path = "" 
        self.current_versions = []
        self.config_file = "config.json"

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
        self.main_frame.grid_rowconfigure((0,1,2,3,4,5,6), weight=1)  # --- 修改：增加一行 ---

        # 1. 标题
        self.label_title = ctk.CTkLabel(master=self.main_frame, text="欢迎使用 NOS Launcher", font=("Microsoft YaHei", 20, "bold"), text_color="#ffffff")
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

        # 4. 新增：打开插件文件夹按钮
        self.addons_button = ctk.CTkButton(
            master=self.main_frame,
            text="打开插件文件夹",
            width=250,
            height=35,
            corner_radius=15,
            font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5",  # 与启动按钮颜色一致
            hover_color="#4a7a9b",
            command=self.open_addons_folder
        )
        self.addons_button.grid(row=4, column=0, pady=10)  # --- 修改：放置在新行 ---

        # 5. 新增：打开预设文件夹按钮
        self.presets_button = ctk.CTkButton(
            master=self.main_frame,
            text="打开预设文件夹",
            width=250,
            height=35,
            corner_radius=15,
            font=("Microsoft YaHei", 13),
            fg_color="#5a8ab5",  # 与启动按钮颜色一致
            hover_color="#4a7a9b",
            command=self.open_presets_folder
        )
        self.presets_button.grid(row=5, column=0, pady=10)  # --- 修改：放置在新行 ---

        # 6. 设置按钮
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
        self.settings_button.grid(row=6, column=0, pady=10)  # --- 修改：调整行号 ---

        # 7. 版本号
        self.version_label_bottom = ctk.CTkLabel(
            master=self.main_frame,
            text="NOS Launcher v1.0.0",
            font=("Microsoft YaHei", 10),
            text_color="#aaaaaa"
        )
        self.version_label_bottom.grid(row=7, column=0, pady=(10, 20))  # --- 修改：调整行号 ---

        # 在所有UI元素创建后，再加载配置
        self.load_config()

    def load_logo(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            png_path = os.path.join(current_dir, "re", "nos.png")
            
            if os.path.exists(png_path):
                pil_image = Image.open(png_path)
                
                max_width = 400
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
                self.logo_label.grid(row=0, column=0, pady=20)
                self.logo_image = logo_image
            else:
                self.show_text_logo("NOS Launcher")
                
        except Exception as e:
            print(f"加载 Logo 失败: {e}")
            self.show_text_logo("NOS Launcher")

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
                if self.game_root_path and os.path.isdir(self.game_root_path):
                    self.scan_game_versions(show_msg=False)
            except:
                pass

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({"game_path": self.game_root_path}, f, ensure_ascii=False, indent=4)
        except:
            pass

    def open_settings(self):
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("设置")
        self.settings_window.geometry("500x350")
        self.settings_window.resizable(False, False)
        self.settings_window.attributes("-topmost", True)
        
        self.update_idletasks()
        x = int(self.winfo_x() + (self.winfo_width()/2) - 250)
        y = int(self.winfo_y() + (self.winfo_height()/2) - 175)
        self.settings_window.geometry(f"500x350+{x}+{y}")

        self.settings_window.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.settings_window, text="启动器设置", font=("Microsoft YaHei", 18, "bold")).grid(row=0, column=0, pady=20)

        self.path_display = ctk.CTkEntry(self.settings_window, width=400, height=35, placeholder_text="请输入或选择游戏根目录")
        self.path_display.grid(row=1, column=0, pady=5, padx=20)
        if self.game_root_path: self.path_display.insert(0, self.game_root_path)

        btn_frame = ctk.CTkFrame(self.settings_window, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=15)
        ctk.CTkButton(btn_frame, text="浏览...", width=100, command=self.browse_folder).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="保存路径", width=100, fg_color="#28a745", hover_color="#218838", command=self.save_manual_path).pack(side="left", padx=10)

        ctk.CTkLabel(self.settings_window, text="只有包含 'Among Us.exe' 的子文件夹才会显示在版本列表中", text_color="gray", font=("Microsoft YaHei", 11)).grid(row=3, column=0, pady=10)

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
                    if os.path.exists(exe_path):
                        versions.append(item)

            if versions:
                self.current_versions = sorted(versions)
                self.version_combobox.configure(values=self.current_versions)
                self.version_combobox.set(self.current_versions[0])
                if show_msg:
                    messagebox.showinfo("成功", f"扫描完成，找到 {len(versions)} 个有效游戏版本。")
            else:
                self.current_versions = []
                self.version_combobox.configure(values=["未找到有效版本"])
                self.version_combobox.set("未找到有效版本")
                if show_msg:
                    messagebox.showwarning("警告", "选中的文件夹内没有包含 'Among Us.exe' 的子文件夹。")

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
            messagebox.showwarning("提示", "请先在设置中添加有效的游戏文件夹并选择一个版本！")
            return
            
        addons_path = os.path.join(self.game_root_path, selected_version, "Addons")
        if os.path.isdir(addons_path):
            try:
                # 使用文件资源管理器打开文件夹
                subprocess.Popen(f'explorer "{addons_path}"')
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：\n{e}")
        else:
            messagebox.showwarning("提示", f"插件文件夹不存在：\n{addons_path}")

    def open_presets_folder(self):
        """打开预设文件夹"""
        selected_version = self.version_combobox.get()
        if not self.game_root_path or selected_version == "请先在设置中添加文件夹" or selected_version == "未找到有效版本":
            messagebox.showwarning("提示", "请先在设置中添加有效的游戏文件夹并选择一个版本！")
            return
            
        presets_path = os.path.join(self.game_root_path, selected_version, "Presets")
        if os.path.isdir(presets_path):
            try:
                # 使用文件资源管理器打开文件夹
                subprocess.Popen(f'explorer "{presets_path}"')
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：\n{e}")
        else:
            messagebox.showwarning("提示", f"预设文件夹不存在：\n{presets_path}")

if __name__ == "__main__":
    app = NOSLauncher()
    app.mainloop()
