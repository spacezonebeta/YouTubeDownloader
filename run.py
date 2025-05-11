#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YouTube批量下载工具启动脚本

这个脚本用于检查环境并启动YouTube批量下载工具。
它会检查必要的依赖是否已安装，并尝试自动安装缺失的依赖。
"""

import os
import sys
import subprocess
import importlib.util
import shutil

def check_module(module_name):
    """检查模块是否已安装"""
    return importlib.util.find_spec(module_name) is not None

def install_requirements():
    """安装所需的依赖包"""
    print("正在检查并安装所需依赖...")    
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    
    if os.path.exists(requirements_path):
        # 读取requirements.txt获取包列表
        try:
            with open(requirements_path, 'r') as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception as e:
            print(f"读取requirements.txt失败：{str(e)}")
            return False
            
        # 首先尝试正常安装
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
            print("依赖安装完成！")
            return True
        except subprocess.CalledProcessError:
            print("正常安装失败，尝试无代理安装...")
            # 尝试使用--no-proxy选项安装
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-proxy", "-r", requirements_path])
                print("依赖安装完成！")
                return True
            except subprocess.CalledProcessError:
                print("尝试使用国内镜像源安装...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "-r", requirements_path])
                    print("依赖安装完成！")
                    return True
                except subprocess.CalledProcessError:
                    print("尝试单独安装各个依赖包...")
                    # 尝试单独安装每个包
                    success = True
                    for package in packages:
                        try:
                            print(f"正在安装 {package}...")
                            # 先尝试使用国内镜像源
                            try:
                                subprocess.check_call([sys.executable, "-m", "pip", "install", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", package])
                            except subprocess.CalledProcessError:
                                # 如果失败，尝试使用--no-proxy选项
                                try:
                                    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-proxy", package])
                                except subprocess.CalledProcessError:
                                    # 如果还是失败，尝试普通安装
                                    try:
                                        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                                    except subprocess.CalledProcessError:
                                        print(f"安装 {package} 失败")
                                        success = False
                        except Exception as e:
                            print(f"安装 {package} 过程出错：{str(e)}")
                            success = False
                    
                    if success:
                        print("所有依赖安装完成！")
                        return True
                    else:
                        print("部分依赖安装失败，尝试离线安装...")
                        return try_offline_install()
        except Exception as e:
            print(f"依赖安装过程出错：{str(e)}")
            print("尝试离线安装...")
            return try_offline_install()
    else:
        print("找不到requirements.txt文件，请确保文件存在")
        return False

def check_ffmpeg():
    """检查FFmpeg是否已安装"""
    try:
        subprocess.check_call(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def try_offline_install():
    """尝试从本地packages目录安装依赖包"""
    print("正在尝试从本地安装依赖...")
    packages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packages")
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    
    if not os.path.exists(packages_dir):
        print(f"本地packages目录不存在，创建目录: {packages_dir}")
        os.makedirs(packages_dir)
        print("请将依赖包下载到此目录后重新运行此脚本")
        print("\n在有网络的电脑上，可以使用以下命令下载依赖包:")
        print(f"pip download -d {packages_dir} -r {requirements_path}")
        print("\n或者运行离线安装脚本:")
        print("python offline_install.py")
        return False
    
    if os.path.exists(requirements_path):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", packages_dir, "-r", requirements_path])
            print("依赖安装完成！")
            return True
        except subprocess.CalledProcessError as e:
            print(f"离线依赖安装失败: {str(e)}")
            print("请确保所有依赖包已下载到packages目录")
            print("\n您可以尝试运行离线安装脚本:")
            print("python offline_install.py")
            return False
    else:
        print("找不到requirements.txt文件，请确保文件存在")
        return False

def update_yt_dlp():
    """更新yt-dlp到最新版本"""
    print("正在更新yt-dlp到最新版本...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        print("yt-dlp更新完成！")
        return True
    except subprocess.CalledProcessError:
        print("通过pip更新失败，尝试使用国内镜像源...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "yt-dlp"])
            print("yt-dlp更新完成！")
            return True
        except subprocess.CalledProcessError:
            print("更新yt-dlp失败，请尝试手动更新")
            return False

def fix_main_py():
    """修复main.py文件中的问题"""
    main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    
    if not os.path.exists(main_path):
        print(f"找不到main.py文件: {main_path}")
        return False
    
    print("正在修复main.py文件...")
    
    # 备份原文件
    backup_path = main_path + ".bak"
    shutil.copy2(main_path, backup_path)
    print(f"已备份原文件到: {backup_path}")
    
    # 读取文件内容
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复设置区域
    if "def create_settings_frame(self):" in content:
        # 移除错误的内部函数定义
        content = content.replace("def create_settings_frame(self):", "# 设置区域")
        
        # 添加正确的设置区域代码
        settings_code = """
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
        """
        
        # 在操作按钮区域后插入设置区域代码
        content = content.replace("# 设置区域\n        def create_settings_frame(self):", settings_code)
    
    # 修复on_closing方法
    if "def on_closing(self):" not in content:
        on_closing_code = """
    def on_closing(self):
        '''关闭窗口时的处理'''
        if hasattr(self, 'downloader') and self.downloader:
            self.downloader.is_cancelled = True
        self.root.destroy()
    """
        # 在类定义的末尾添加on_closing方法
        content = content.replace("if __name__ == \"__main__\":", on_closing_code + "\n\nif __name__ == \"__main__\":")
    
    # 写入修改后的内容
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("main.py文件修复完成！")
    return True

def fix_ytdlp_downloader():
    """修复ytdlp_downloader.py文件中的问题"""
    downloader_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ytdlp_downloader.py")
    
    if not os.path.exists(downloader_path):
        print(f"找不到ytdlp_downloader.py文件: {downloader_path}")
        return False
    
    print("正在修复ytdlp_downloader.py文件...")
    
    # 备份原文件
    backup_path = downloader_path + ".bak"
    shutil.copy2(downloader_path, backup_path)
    print(f"已备份原文件到: {backup_path}")
    
    # 读取文件内容
    with open(downloader_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新_get_format_code方法以支持2K和4K
    if "_get_format_code" in content:
        old_format_code = """    def _get_format_code(self, quality, video_only=False):
        \"\"\"根据质量获取格式代码\"\"\"
        if video_only:
            # 仅视频格式
            if quality == "最高质量":
                return "bestvideo[ext=mp4]/best[ext=mp4]/best"
            elif quality == "1080p":
                return "bestvideo[height<=1080][ext=mp4]/best[height<=1080][ext=mp4]/best"
            elif quality == "720p":
                return "bestvideo[height<=720][ext=mp4]/best[height<=720][ext=mp4]/best"
            elif quality == "480p":
                return "bestvideo[height<=480][ext=mp4]/best[height<=480][ext=mp4]/best"
            elif quality == "360p":
                return "bestvideo[height<=360][ext=mp4]/best[height<=360][ext=mp4]/best"
            else:
                return "bestvideo[ext=mp4]/best[ext=mp4]/best"
        else:
            # 视频+音频格式
            if quality == "最高质量":
                return "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
            elif quality == "1080p":
                return "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080][ext=mp4]/best"
            elif quality == "720p":
                return "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720][ext=mp4]/best"
            elif quality == "480p":
                return "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480][ext=mp4]/best"
            elif quality == "360p":
                return "bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360][ext=mp4]/best"
            else:
                return "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best\""""
        
        new_format_code = """    def _get_format_code(self, quality, video_only=False):
        \"\"\"根据质量获取格式代码\"\"\"
        if video_only:
            # 仅视频格式
            if quality == "最高质量":
                return "bestvideo[ext=mp4]/best[ext=mp4]/best"
            elif quality == "4K":
                return "bestvideo[height<=2160][ext=mp4]/best[height<=2160][ext=mp4]/best"
            elif quality == "2K":
                return "bestvideo[height<=1440][ext=mp4]/best[height<=1440][ext=mp4]/best"
            elif quality == "1080p":
                return "bestvideo[height<=1080][ext=mp4]/best[height<=1080][ext=mp4]/best"
            elif quality == "720p":
                return "bestvideo[height<=720][ext=mp4]/best[height<=720][ext=mp4]/best"
            elif quality == "480p":
                return "bestvideo[height<=480][ext=mp4]/best[height<=480][ext=mp4]/best"
            elif quality == "360p":
                return "bestvideo[height<=360][ext=mp4]/best[height<=360][ext=mp4]/best"
            else:
                return "bestvideo[ext=mp4]/best[ext=mp4]/best"
        else:
            # 视频+音频格式
            if quality == "最高质量":
                return "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
            elif quality == "4K":
                return "bestvideo[height<=2160][ext=mp4]+bestaudio/best[height<=2160][ext=mp4]/best"
            elif quality == "2K":
                return "bestvideo[height<=1440][ext=mp4]+bestaudio/best[height<=1440][ext=mp4]/best"
            elif quality == "1080p":
                return "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080][ext=mp4]/best"
            elif quality == "720p":
                return "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720][ext=mp4]/best"
            elif quality == "480p":
                return "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480][ext=mp4]/best"
            elif quality == "360p":
                return "bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360][ext=mp4]/best"
            else:
                return "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best\""""
        
        content = content.replace(old_format_code, new_format_code)
    
    # 写入修改后的内容
    with open(downloader_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("ytdlp_downloader.py文件修复完成！")
    return True

def main():
    print("===== YouTube下载工具修复脚本 =====")
    print("这个脚本将修复添加2K和4K支持后出现的问题")
    
    # 更新yt-dlp
    update_yt_dlp()
    
    # 修复main.py
    main_fixed = fix_main_py()
    
    # 修复ytdlp_downloader.py
    downloader_fixed = fix_ytdlp_downloader()
    
    if main_fixed and downloader_fixed:
        print("\n修复完成！现在应该可以正常使用YouTube下载工具了")
        print("请重新运行程序: python main.py")
    else:
        print("\n部分修复可能未成功，请检查上述输出信息")
    
    print("\n按Enter键退出...")
    input()

if __name__ == "__main__":
    main()