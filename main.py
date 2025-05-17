import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import configparser
from ytdlp_downloader import YtdlpDownloader  # 导入基于yt-dlp的下载器
from config_manager import ConfigManager
import urllib.request
import zipfile
import shutil
import tempfile

# 尝试导入代理管理器
try:
    from proxy_manager import ProxyManager
    has_proxy_manager = True
except ImportError:
    has_proxy_manager = False

def check_and_download_ffmpeg(ffmpeg_dir):
    import platform
    import stat

    # 检查ffmpeg是否已存在
    ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if os.path.exists(ffmpeg_exe):
        return ffmpeg_exe

    # 下载windows版ffmpeg静态编译包
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = os.path.join(ffmpeg_dir, "ffmpeg.zip")
    print("正在下载ffmpeg，请稍候...")
    urllib.request.urlretrieve(url, zip_path)

    # 解压ffmpeg.exe
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for name in zip_ref.namelist():
            if name.endswith("ffmpeg.exe"):
                zip_ref.extract(name, ffmpeg_dir)
                src = os.path.join(ffmpeg_dir, name)
                dst = os.path.join(ffmpeg_dir, "ffmpeg.exe")
                shutil.move(src, dst)
                # 设置可执行权限
                os.chmod(dst, stat.S_IEXEC)
                break
    os.remove(zip_path)
    return ffmpeg_exe

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube批量下载工具")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.download_path = self.config_manager.get_download_path()
        
        # 初始化代理管理器
        self.proxy_manager = ProxyManager() if has_proxy_manager else None
        
        # 使用基于yt-dlp的下载器
        try:
            self.downloader = YtdlpDownloader(self.download_path)
            print("已启用yt-dlp下载器，提供更可靠的下载体验和更好的错误处理")
        except Exception as e:
            print(f"yt-dlp下载器初始化失败: {str(e)}")
            raise
        
        # 创建主框架
        self.create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建输入区域
        input_frame = ttk.LabelFrame(main_frame, text="输入YouTube链接", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # 单个链接输入
        single_link_frame = ttk.Frame(input_frame)
        single_link_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(single_link_frame, text="单个链接:").pack(side=tk.LEFT, padx=5)
        self.single_link_entry = ttk.Entry(single_link_frame)
        self.single_link_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(single_link_frame, text="添加", command=self.add_single_link).pack(side=tk.LEFT, padx=5)
        
        # 批量链接输入
        batch_link_frame = ttk.Frame(input_frame)
        batch_link_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(batch_link_frame, text="批量链接:").pack(side=tk.LEFT, padx=5)
        self.batch_link_text = tk.Text(batch_link_frame, height=5)
        self.batch_link_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(batch_link_frame, text="添加", command=self.add_batch_links).pack(side=tk.LEFT, padx=5)
        
        # 链接列表区域
        links_frame = ttk.LabelFrame(main_frame, text="下载队列", padding="10")
        links_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建表格
        columns = ("序号", "链接", "状态", "进度")
        self.links_tree = ttk.Treeview(links_frame, columns=columns, show="headings")
        
        # 设置列标题
        for col in columns:
            self.links_tree.heading(col, text=col)
        
        # 设置列宽
        self.links_tree.column("序号", width=50)
        self.links_tree.column("链接", width=350)
        self.links_tree.column("状态", width=100)
        self.links_tree.column("进度", width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(links_frame, orient=tk.VERTICAL, command=self.links_tree.yview)
        self.links_tree.configure(yscroll=scrollbar.set)
        
        # 放置表格和滚动条
        self.links_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 设置下载路径
        path_frame = ttk.Frame(button_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="下载路径:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar(value=self.download_path)
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var, state="readonly")
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_path).pack(side=tk.LEFT, padx=5)
        
        # 操作按钮
        action_frame = ttk.Frame(button_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="开始下载", command=self.start_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="暂停", command=self.pause_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="继续", command=self.resume_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="取消", command=self.cancel_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="清空列表", command=self.clear_list).pack(side=tk.LEFT, padx=5)
        
        # 设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="下载设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 创建设置选项
        settings_inner_frame = ttk.Frame(settings_frame)
        settings_inner_frame.pack(fill=tk.X, pady=5)
        
        # 视频质量选择
        ttk.Label(settings_inner_frame, text="视频质量:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.quality_var = tk.StringVar(value="1080p")
        quality_combo = ttk.Combobox(settings_inner_frame, textvariable=self.quality_var, width=10)
        quality_combo['values'] = ('最高质量', '4K', '2K', '1080p', '720p', '480p', '360p')
        quality_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 下载类型选择
        ttk.Label(settings_inner_frame, text="下载类型:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.type_var = tk.StringVar(value="视频+音频")
        type_combo = ttk.Combobox(settings_inner_frame, textvariable=self.type_var, width=10)
        type_combo['values'] = ('视频+音频', '仅视频', '仅音频')
        type_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 代理设置
        if self.proxy_manager:
            proxy_frame = ttk.Frame(settings_inner_frame)
            proxy_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
            
            self.proxy_enabled_var = tk.BooleanVar(value=self.proxy_manager.is_proxy_enabled())
            ttk.Checkbutton(proxy_frame, text="启用代理", variable=self.proxy_enabled_var, command=self.toggle_proxy).pack(side=tk.LEFT, padx=5)
            ttk.Button(proxy_frame, text="测试代理", command=self.test_proxy).pack(side=tk.LEFT, padx=5)
            ttk.Button(proxy_frame, text="配置代理", command=self.configure_proxy).pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
    
    def add_single_link(self):
        link = self.single_link_entry.get().strip()
        if link:
            self.add_link_to_list(link)
            self.single_link_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("警告", "请输入有效的YouTube链接")
    
    def add_batch_links(self):
        links_text = self.batch_link_text.get(1.0, tk.END).strip()
        if links_text:
            links = [link.strip() for link in links_text.split('\n') if link.strip()]
            for link in links:
                self.add_link_to_list(link)
            self.batch_link_text.delete(1.0, tk.END)
        else:
            messagebox.showwarning("警告", "请输入有效的YouTube链接")
    
    def add_link_to_list(self, link):
        # 检查链接是否已存在
        for item in self.links_tree.get_children():
            if self.links_tree.item(item, 'values')[1] == link:
                messagebox.showinfo("提示", f"链接已存在: {link}")
                return
        
        # 添加到列表
        item_id = len(self.links_tree.get_children()) + 1
        self.links_tree.insert("", tk.END, values=(item_id, link, "等待中", "0%"))
    
    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.download_path = path
            self.path_var.set(path)
            self.config_manager.set_download_path(path)
            self.downloader.set_download_path(path)
    
    def start_download(self):
        links = []
        for item in self.links_tree.get_children():
            values = self.links_tree.item(item, 'values')
            if values[2] != "完成":
                links.append((item, values[1]))
        
        if not links:
            messagebox.showinfo("提示", "没有待下载的链接")
            return
        
        # 获取设置
        quality = self.quality_var.get()
        download_type = self.type_var.get()
        
        # 开始下载线程
        threading.Thread(target=self.download_thread, args=(links, quality, download_type), daemon=True).start()
        self.status_var.set("下载中...")
    
    def toggle_proxy(self):
        """切换代理状态"""
        if self.proxy_manager:
            enabled = self.proxy_enabled_var.get()
            self.proxy_manager.set_proxy_enabled(enabled)
            self.proxy_manager.save_config()
            status = "启用" if enabled else "禁用"
            self.status_var.set(f"已{status}代理设置")
    
    def test_proxy(self):
        """测试代理连接"""
        if not self.proxy_manager:
            return
            
        # 禁用界面
        self.root.config(cursor="wait")
        self.status_var.set("正在测试代理连接...")
        self.root.update()
        
        # 在新线程中测试代理
        def test_thread():
            success, message = self.proxy_manager.test_proxy_connection()
            
            # 更新界面
            self.root.config(cursor="")
            if success:
                self.status_var.set(f"代理连接测试成功: {message}")
                messagebox.showinfo("代理测试", f"代理连接测试成功: {message}")
            else:
                self.status_var.set(f"代理连接测试失败: {message}")
                messagebox.showerror("代理测试", f"代理连接测试失败: {message}")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def configure_proxy(self):
        """配置代理设置"""
        if not self.proxy_manager:
            return
            
        # 创建配置窗口
        proxy_window = tk.Toplevel(self.root)
        proxy_window.title("代理设置")
        proxy_window.geometry("500x250")
        proxy_window.resizable(False, False)
        proxy_window.transient(self.root)
        proxy_window.grab_set()
        
        # 创建表单
        frame = ttk.Frame(proxy_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 代理启用开关
        enabled_var = tk.BooleanVar(value=self.proxy_manager.is_proxy_enabled())
        ttk.Checkbutton(frame, text="启用代理", variable=enabled_var).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # HTTP代理
        ttk.Label(frame, text="HTTP代理:").grid(row=1, column=0, sticky=tk.W, pady=5)
        http_proxy_var = tk.StringVar(value=self.proxy_manager.get_http_proxy())
        ttk.Entry(frame, textvariable=http_proxy_var, width=40).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # HTTPS代理
        ttk.Label(frame, text="HTTPS代理:").grid(row=2, column=0, sticky=tk.W, pady=5)
        https_proxy_var = tk.StringVar(value=self.proxy_manager.get_https_proxy())
        ttk.Entry(frame, textvariable=https_proxy_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 无需代理的地址
        ttk.Label(frame, text="无需代理的地址:").grid(row=3, column=0, sticky=tk.W, pady=5)
        no_proxy_var = tk.StringVar(value=self.proxy_manager.get_no_proxy())
        ttk.Entry(frame, textvariable=no_proxy_var, width=40).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 自动检测系统代理
        ttk.Button(frame, text="自动检测系统代理", command=lambda: self.auto_detect_proxy(http_proxy_var, https_proxy_var)).grid(row=4, column=0, columnspan=2, pady=10)
        
        # 保存按钮
        def save_proxy():
            self.proxy_manager.set_proxy_enabled(enabled_var.get())
            self.proxy_manager.set_http_proxy(http_proxy_var.get())
            self.proxy_manager.set_https_proxy(https_proxy_var.get())
            self.proxy_manager.set_no_proxy(no_proxy_var.get())
            self.proxy_manager.save_config()
            self.proxy_enabled_var.set(enabled_var.get())
            self.status_var.set("代理设置已保存")
            proxy_window.destroy()
        
        ttk.Button(frame, text="保存", command=save_proxy).grid(row=5, column=0, pady=10)
        ttk.Button(frame, text="取消", command=proxy_window.destroy).grid(row=5, column=1, pady=10)
    
    def auto_detect_proxy(self, http_proxy_var, https_proxy_var):
        """自动检测系统代理设置"""
        if not self.proxy_manager:
            return
            
        http_proxy, https_proxy = self.proxy_manager.get_system_proxy()
        if http_proxy or https_proxy:
            http_proxy_var.set(http_proxy)
            https_proxy_var.set(https_proxy)
            messagebox.showinfo("自动检测", f"已检测到系统代理设置:\nHTTP代理: {http_proxy}\nHTTPS代理: {https_proxy}")
        else:
            messagebox.showinfo("自动检测", "未检测到系统代理设置")
    
    def download_thread(self, links, quality, download_type):
        for item_id, link in links:
            # 更新状态
            self.root.after(0, lambda i=item_id: self.links_tree.item(i, values=(
                self.links_tree.item(i, 'values')[0],
                self.links_tree.item(i, 'values')[1],
                "下载中",
                "0%"
            )))
            
            try:
                # 设置进度回调
                def progress_callback(progress, status_text=None, i=item_id):
                    # 支持增强版下载器的状态文本
                    status = "下载中"
                    progress_text = f"{int(progress*100)}%"
                    
                    # 如果提供了状态文本，显示在进度中
                    if status_text:
                        progress_text = status_text
                    
                    self.root.after(0, lambda p=progress, i=i: self.links_tree.item(i, values=(
                        self.links_tree.item(i, 'values')[0],
                        self.links_tree.item(i, 'values')[1],
                        status,
                        progress_text
                    )))
                
                # 执行下载，传递代理设置
                use_proxy = self.proxy_enabled_var.get() if hasattr(self, 'proxy_enabled_var') else None
                
                # 检查下载器是否支持代理参数
                if hasattr(self.downloader, 'download') and 'use_proxy' in self.downloader.download.__code__.co_varnames:
                    self.downloader.download(link, quality, download_type, progress_callback, use_proxy=use_proxy)
                else:
                    self.downloader.download(link, quality, download_type, progress_callback)
                
                # 更新状态为完成
                self.root.after(0, lambda i=item_id: self.links_tree.item(i, values=(
                    self.links_tree.item(i, 'values')[0],
                    self.links_tree.item(i, 'values')[1],
                    "完成",
                    "100%"
                )))
            except Exception as e:
                # 更新状态为错误
                self.root.after(0, lambda i=item_id, e=str(e): self.links_tree.item(i, values=(
                    self.links_tree.item(i, 'values')[0],
                    self.links_tree.item(i, 'values')[1],
                    "错误",
                    str(e)[:20]
                )))
        
        # 更新状态栏
        self.root.after(0, lambda: self.status_var.set("下载完成"))
    
    def pause_download(self):
        self.downloader.pause()
        self.status_var.set("已暂停")
    
    def resume_download(self):
        self.downloader.resume()
        self.status_var.set("下载中...")
    
    def cancel_download(self):
        self.downloader.cancel()
        self.status_var.set("已取消")
        
        # 更新所有未完成的项目状态
        for item in self.links_tree.get_children():
            values = self.links_tree.item(item, 'values')
            if values[2] == "下载中" or values[2] == "等待中":
                self.links_tree.item(item, values=(
                    values[0], values[1], "已取消", values[3]
                ))
    
    def clear_list(self):
        # 清空列表前先取消下载
        self.cancel_download()
        self.links_tree.delete(*self.links_tree.get_children())
        self.status_var.set("就绪")
    
    def on_closing(self):
        # 关闭前取消下载
        self.cancel_download()
        self.root.destroy()

    def update_progress(self, progress, status_text=None, url=None):
        """更新下载进度，支持多任务"""
        def update():
            for item in self.links_tree.get_children():
                values = self.links_tree.item(item, 'values')
                if url and values[1] == url:
                    self.links_tree.item(item, values=(
                        values[0],
                        values[1],
                        status_text or "下载中",
                        f"{progress}%"
                    ))
                    break
        self.root.after(0, update)

def main():
    # 确保下载目录存在
    config = ConfigManager()
    download_path = config.get_download_path()
    try:
        os.makedirs(download_path, exist_ok=True)
    except (PermissionError, FileNotFoundError) as e:
        # 如果创建目录失败，尝试使用临时目录
        temp_path = os.path.join(tempfile.gettempdir(), "YouTubeDownloader")
        try:
            os.makedirs(temp_path, exist_ok=True)
            config.set_download_path(temp_path)
            download_path = temp_path
        except Exception as e2:
            messagebox.showerror("错误", f"无法创建下载目录：\n{str(e)}\n尝试使用临时目录也失败：\n{str(e2)}\n请手动选择下载目录。")
            return

    # 检查ffmpeg
    ffmpeg_dir = os.path.abspath(os.path.dirname(__file__))
    ffmpeg_path = check_and_download_ffmpeg(ffmpeg_dir)
    # 把ffmpeg目录加入环境变量，确保yt-dlp能找到
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    # 启动应用
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

# 在下载按钮的点击事件处理函数中添加高分辨率提示
def download_video(self):
    """下载单个视频"""
    url = self.url_var.get().strip()
    if not url:
        messagebox.showwarning("警告", "请输入YouTube视频链接")
        return
    
    output_path = self.output_var.get()
    if not output_path or not os.path.isdir(output_path):
        messagebox.showwarning("警告", "请选择有效的输出目录")
        return
    
    resolution = self.quality_var.get()
    
    # 添加高分辨率提示
    if resolution in ["4K", "2K"]:
        if not messagebox.askyesno("提示", f"您选择了{resolution}分辨率，下载可能需要较长时间，且文件较大。是否继续？"):
            return
    
    # ... existing code ...