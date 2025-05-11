#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理配置向导

这个模块提供了一个简单的向导界面，帮助用户配置代理设置，
并测试代理连接是否正常工作。
"""

import os
import sys
import socket
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import urlparse

# 导入代理管理器
try:
    from proxy_manager import ProxyManager
except ImportError:
    print("错误: 找不到代理管理器模块")
    sys.exit(1)

class ProxyWizard:
    """代理配置向导类"""
    
    def __init__(self, root):
        """初始化代理配置向导
        
        Args:
            root: tkinter根窗口
        """
        self.root = root
        self.root.title("YouTube下载器 - 代理配置向导")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 初始化代理管理器
        self.proxy_manager = ProxyManager()
        
        # 创建界面
        self._create_widgets()
        
        # 加载当前配置
        self._load_current_config()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="代理配置向导", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # 说明文本
        desc_text = (
            "此向导将帮助您配置代理设置，以解决YouTube下载时的连接问题。\n"
            "如果您遇到HTTP Error 400或其他网络连接错误，正确配置代理可能会有所帮助。"
        )
        desc_label = ttk.Label(main_frame, text=desc_text, wraplength=550)
        desc_label.pack(pady=10, fill=tk.X)
        
        # 创建设置框架
        settings_frame = ttk.LabelFrame(main_frame, text="代理设置", padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 启用代理选项
        self.enable_proxy_var = tk.BooleanVar()
        enable_proxy_check = ttk.Checkbutton(
            settings_frame, 
            text="启用代理", 
            variable=self.enable_proxy_var,
            command=self._toggle_proxy_fields
        )
        enable_proxy_check.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # HTTP代理
        http_label = ttk.Label(settings_frame, text="HTTP代理:")
        http_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.http_proxy_var = tk.StringVar()
        self.http_proxy_entry = ttk.Entry(settings_frame, textvariable=self.http_proxy_var, width=50)
        self.http_proxy_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # HTTPS代理
        https_label = ttk.Label(settings_frame, text="HTTPS代理:")
        https_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.https_proxy_var = tk.StringVar()
        self.https_proxy_entry = ttk.Entry(settings_frame, textvariable=self.https_proxy_var, width=50)
        self.https_proxy_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 无需代理的地址
        no_proxy_label = ttk.Label(settings_frame, text="无需代理的地址:")
        no_proxy_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.no_proxy_var = tk.StringVar()
        self.no_proxy_entry = ttk.Entry(settings_frame, textvariable=self.no_proxy_var, width=50)
        self.no_proxy_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 格式提示
        format_text = "格式: http(s)://主机名:端口号 (例如: http://127.0.0.1:7890)"
        format_label = ttk.Label(settings_frame, text=format_text, font=("Arial", 9))
        format_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 自动检测按钮
        detect_button = ttk.Button(
            settings_frame, 
            text="自动检测系统代理", 
            command=self._auto_detect_proxy
        )
        detect_button.grid(row=5, column=0, sticky=tk.W, pady=10)
        
        # 测试连接按钮
        test_button = ttk.Button(
            settings_frame, 
            text="测试连接", 
            command=self._test_connection
        )
        test_button.grid(row=5, column=1, sticky=tk.W, pady=10)
        
        # 状态标签
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 10))
        status_label.pack(pady=10)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 保存按钮
        save_button = ttk.Button(
            button_frame, 
            text="保存设置", 
            command=self._save_settings
        )
        save_button.pack(side=tk.RIGHT, padx=5)
        
        # 取消按钮
        cancel_button = ttk.Button(
            button_frame, 
            text="取消", 
            command=self.root.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def _load_current_config(self):
        """加载当前配置"""
        # 设置启用状态
        self.enable_proxy_var.set(self.proxy_manager.is_proxy_enabled())
        
        # 设置代理值
        self.http_proxy_var.set(self.proxy_manager.get_http_proxy())
        self.https_proxy_var.set(self.proxy_manager.get_https_proxy())
        self.no_proxy_var.set(self.proxy_manager.get_no_proxy())
        
        # 更新界面状态
        self._toggle_proxy_fields()
    
    def _toggle_proxy_fields(self):
        """切换代理字段的启用状态"""
        state = "normal" if self.enable_proxy_var.get() else "disabled"
        self.http_proxy_entry.config(state=state)
        self.https_proxy_entry.config(state=state)
        self.no_proxy_entry.config(state=state)
    
    def _auto_detect_proxy(self):
        """自动检测系统代理"""
        self.status_var.set("正在检测系统代理...")
        self.root.update()
        
        http_proxy, https_proxy = self.proxy_manager.get_system_proxy()
        
        if http_proxy or https_proxy:
            self.enable_proxy_var.set(True)
            self.http_proxy_var.set(http_proxy)
            self.https_proxy_var.set(https_proxy)
            self._toggle_proxy_fields()
            self.status_var.set(f"已检测到系统代理: HTTP={http_proxy}, HTTPS={https_proxy}")
            messagebox.showinfo("检测成功", "已成功检测到系统代理设置")
        else:
            self.status_var.set("未检测到系统代理设置")
            messagebox.showinfo("检测结果", "未检测到系统代理设置，请手动配置")
    
    def _validate_proxy_url(self, url):
        """验证代理URL格式
        
        Args:
            url: 代理URL
            
        Returns:
            bool: 格式是否有效
        """
        if not url:
            return True  # 空URL是有效的
        
        try:
            parsed = urlparse(url)
            return all([
                parsed.scheme in ('http', 'https'),
                parsed.netloc
            ])
        except Exception:
            return False
    
    def _test_connection(self):
        """测试代理连接"""
        # 保存当前设置到临时配置
        temp_enabled = self.proxy_manager.is_proxy_enabled()
        temp_http = self.proxy_manager.get_http_proxy()
        temp_https = self.proxy_manager.get_https_proxy()
        
        # 应用当前界面设置
        self.proxy_manager.set_proxy_enabled(self.enable_proxy_var.get())
        self.proxy_manager.set_http_proxy(self.http_proxy_var.get())
        self.proxy_manager.set_https_proxy(self.https_proxy_var.get())
        
        # 验证代理格式
        if self.enable_proxy_var.get():
            http_proxy = self.http_proxy_var.get()
            https_proxy = self.https_proxy_var.get()
            
            if http_proxy and not self._validate_proxy_url(http_proxy):
                messagebox.showerror("格式错误", f"HTTP代理格式无效: {http_proxy}\n正确格式: http(s)://主机名:端口号")
                return
            
            if https_proxy and not self._validate_proxy_url(https_proxy):
                messagebox.showerror("格式错误", f"HTTPS代理格式无效: {https_proxy}\n正确格式: http(s)://主机名:端口号")
                return
        
        # 更新状态
        self.status_var.set("正在测试连接...")
        self.root.update()
        
        # 测试连接
        success, message = self.proxy_manager.test_proxy_connection()
        
        # 恢复原始设置
        self.proxy_manager.set_proxy_enabled(temp_enabled)
        self.proxy_manager.set_http_proxy(temp_http)
        self.proxy_manager.set_https_proxy(temp_https)
        
        # 显示结果
        if success:
            self.status_var.set("连接测试成功")
            messagebox.showinfo("测试成功", "代理连接测试成功！")
        else:
            self.status_var.set(f"连接测试失败: {message}")
            
            # 提供详细的错误信息和建议
            error_msg = f"代理连接测试失败: {message}\n\n"
            
            # 根据错误类型提供建议
            if "代理格式错误" in message:
                error_msg += "请检查代理格式是否正确，应为 http(s)://主机名:端口号"
            elif "代理服务器拒绝连接" in message:
                error_msg += "请检查代理服务器是否在线，以及端口是否正确"
            elif "代理服务器需要认证" in message:
                error_msg += "请在代理URL中包含用户名和密码，格式为 http(s)://用户名:密码@主机名:端口号"
            elif "无法连接到代理服务器" in message:
                error_msg += "请检查代理地址和端口是否正确，以及代理服务器是否在线"
            elif "DNS解析失败" in message:
                error_msg += "请检查网络连接和DNS设置"
            else:
                error_msg += "\n建议:\n1. 检查代理服务器是否在线\n2. 确认代理地址和端口是否正确\n3. 尝试使用不同的代理服务器"
            
            messagebox.showerror("测试失败", error_msg)
    
    def _save_settings(self):
        """保存设置"""
        # 验证代理格式
        if self.enable_proxy_var.get():
            http_proxy = self.http_proxy_var.get()
            https_proxy = self.https_proxy_var.get()
            
            if http_proxy and not self._validate_proxy_url(http_proxy):
                messagebox.showerror("格式错误", f"HTTP代理格式无效: {http_proxy}\n正确格式: http(s)://主机名:端口号")
                return
            
            if https_proxy and not self._validate_proxy_url(https_proxy):
                messagebox.showerror("格式错误", f"HTTPS代理格式无效: {https_proxy}\n正确格式: http(s)://主机名:端口号")
                return
            
            if not http_proxy and not https_proxy:
                messagebox.showerror("配置错误", "启用代理时，必须至少配置一个HTTP或HTTPS代理")
                return
        
        # 保存设置
        self.proxy_manager.set_proxy_enabled(self.enable_proxy_var.get())
        self.proxy_manager.set_http_proxy(self.http_proxy_var.get())
        self.proxy_manager.set_https_proxy(self.https_proxy_var.get())
        self.proxy_manager.set_no_proxy(self.no_proxy_var.get())
        self.proxy_manager.save_config()
        
        # 应用设置
        self.proxy_manager.apply_proxy_settings()
        
        # 显示成功消息
        self.status_var.set("设置已保存")
        messagebox.showinfo("保存成功", "代理设置已成功保存")

def main():
    """主函数"""
    root = tk.Tk()
    app = ProxyWizard(root)
    root.mainloop()

if __name__ == "__main__":
    main()