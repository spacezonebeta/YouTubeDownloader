#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YouTube批量下载工具离线安装脚本

这个脚本用于在无法连接网络或代理有问题的情况下安装依赖。
它会尝试从本地packages目录安装依赖包。
"""

import os
import sys
import subprocess
import importlib.util

def check_module(module_name):
    """检查模块是否已安装"""
    return importlib.util.find_spec(module_name) is not None

def install_from_local():
    """从本地packages目录安装依赖包"""
    print("正在尝试从本地安装依赖...")
    packages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packages")
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    
    if not os.path.exists(packages_dir):
        print(f"本地packages目录不存在，创建目录: {packages_dir}")
        os.makedirs(packages_dir)
        print("请将依赖包下载到此目录后重新运行此脚本")
        print("\n在有网络的电脑上，可以使用以下命令下载依赖包:")
        print(f"pip download -d {packages_dir} -r {requirements_path}")
        return False
    
    if os.path.exists(requirements_path):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", packages_dir, "-r", requirements_path])
            print("依赖安装完成！")
            return True
        except subprocess.CalledProcessError as e:
            print(f"依赖安装失败: {str(e)}")
            print("请确保所有依赖包已下载到packages目录")
            return False
    else:
        print("找不到requirements.txt文件，请确保文件存在")
        return False

def main():
    # 检查必要的依赖
    required_modules = ["yt_dlp", "PIL"]
    missing_modules = [module for module in required_modules if not check_module(module)]
    
    if missing_modules:
        print(f"缺少以下依赖: {', '.join(missing_modules)}")
        if not install_from_local():
            print("\n离线安装失败，请参考以下步骤:")
            print("1. 在有网络的电脑上下载依赖包:")
            packages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packages")
            requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
            print(f"   pip download -d {packages_dir} -r {requirements_path}")
            print("2. 将下载的packages目录复制到此电脑")
            print("3. 重新运行此脚本")
            return
    else:
        print("所有依赖已安装")
    
    print("\n安装完成，现在可以运行YouTube批量下载工具:")
    print("python run.py")

if __name__ == "__main__":
    main()