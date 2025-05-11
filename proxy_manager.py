#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理管理器模块

这个模块用于管理YouTube下载器的代理设置，
可以帮助解决HTTP Error 400问题。
"""

import os
import configparser
import logging
import requests
import socket
import urllib.request

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proxy_manager')

class ProxyManager:
    """代理管理器类，用于管理和测试代理设置"""
    
    def __init__(self, config_file="config.ini"):
        """初始化代理管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)
        self.config = configparser.ConfigParser()
        
        # 加载配置
        self.load_config()
        
        # 确保代理配置部分存在
        if not self.config.has_section('Proxy'):
            self.config.add_section('Proxy')
            self.config['Proxy']['enabled'] = 'false'
            self.config['Proxy']['http_proxy'] = ''
            self.config['Proxy']['https_proxy'] = ''
            self.config['Proxy']['no_proxy'] = 'localhost,127.0.0.1'
            self.save_config()
    
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding="utf-8")
    
    def save_config(self):
        """保存配置"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)
    
    def is_proxy_enabled(self):
        """检查代理是否启用"""
        return self.config.getboolean('Proxy', 'enabled', fallback=False)
    
    def set_proxy_enabled(self, enabled):
        """设置代理启用状态
        
        Args:
            enabled: 是否启用代理
        """
        self.config['Proxy']['enabled'] = str(enabled).lower()
        self.save_config()
    
    def get_http_proxy(self):
        """获取HTTP代理"""
        return self.config.get('Proxy', 'http_proxy', fallback='')
    
    def get_https_proxy(self):
        """获取HTTPS代理"""
        return self.config.get('Proxy', 'https_proxy', fallback='')
    
    def get_no_proxy(self):
        """获取无需代理的地址列表"""
        return self.config.get('Proxy', 'no_proxy', fallback='localhost,127.0.0.1')
    
    def set_http_proxy(self, proxy):
        """设置HTTP代理
        
        Args:
            proxy: HTTP代理地址，格式为 http://host:port
        """
        self.config['Proxy']['http_proxy'] = proxy
        self.save_config()
    
    def set_https_proxy(self, proxy):
        """设置HTTPS代理
        
        Args:
            proxy: HTTPS代理地址，格式为 https://host:port
        """
        self.config['Proxy']['https_proxy'] = proxy
        self.save_config()
    
    def set_no_proxy(self, no_proxy):
        """设置无需代理的地址列表
        
        Args:
            no_proxy: 无需代理的地址列表，以逗号分隔
        """
        self.config['Proxy']['no_proxy'] = no_proxy
        self.save_config()
    
    def apply_proxy_settings(self):
        """应用代理设置到环境变量"""
        if self.is_proxy_enabled():
            # 设置环境变量
            os.environ['HTTP_PROXY'] = self.get_http_proxy()
            os.environ['HTTPS_PROXY'] = self.get_https_proxy()
            os.environ['NO_PROXY'] = self.get_no_proxy()
            logger.info(f"已启用代理: HTTP={self.get_http_proxy()}, HTTPS={self.get_https_proxy()}")
            return True
        else:
            # 清除环境变量
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']
            if 'NO_PROXY' in os.environ:
                del os.environ['NO_PROXY']
            logger.info("已禁用代理")
            return False
    
    def test_proxy_connection(self, test_url="https://www.youtube.com"):
        """测试代理连接
        
        Args:
            test_url: 测试URL
            
        Returns:
            (bool, str): 测试结果和错误信息
        """
        try:
            # 应用代理设置
            self.apply_proxy_settings()
            
            # 创建代理字典
            proxies = {}
            if self.is_proxy_enabled():
                http_proxy = self.get_http_proxy()
                https_proxy = self.get_https_proxy()
                if http_proxy:
                    proxies['http'] = http_proxy
                if https_proxy:
                    proxies['https'] = https_proxy
                
                # 验证代理格式
                for proxy_type, proxy_url in proxies.items():
                    if not self._validate_proxy_format(proxy_url):
                        return False, f"代理格式错误: {proxy_url}，正确格式应为 http(s)://host:port"
            
            # 设置超时时间
            timeout = 10
            
            # 先测试DNS解析
            try:
                host = test_url.split('://')[1].split('/')[0]
                socket.gethostbyname(host)
                logger.info(f"DNS解析成功: {host}")
            except Exception as e:
                logger.error(f"DNS解析失败: {str(e)}")
                return False, f"DNS解析失败: 无法解析 {host}，请检查网络连接或DNS设置"
            
            # 发送请求
            logger.info(f"开始测试连接: {test_url} {'使用代理' if proxies else '不使用代理'}")
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            
            # 检查响应状态码
            if response.status_code == 200:
                logger.info(f"代理连接测试成功: {test_url}")
                return True, "连接成功"
            else:
                logger.warning(f"代理连接测试失败: 状态码 {response.status_code}")
                return False, f"连接失败: 状态码 {response.status_code}，请检查代理服务器是否支持HTTPS连接"
                
        except requests.exceptions.ProxyError as e:
            logger.error(f"代理错误: {str(e)}")
            error_details = self._analyze_proxy_error(str(e))
            return False, f"代理错误: {error_details}"
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL错误: {str(e)}")
            return False, f"SSL错误: 代理服务器可能不支持HTTPS连接或证书有问题"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接错误: {str(e)}")
            error_details = self._analyze_connection_error(str(e))
            return False, f"连接错误: {error_details}"
        except requests.exceptions.Timeout as e:
            logger.error(f"连接超时: {str(e)}")
            return False, f"连接超时: 代理服务器响应时间过长，请检查代理服务器状态或网络连接"
        except Exception as e:
            logger.error(f"测试代理连接时出错: {str(e)}")
            return False, f"未知错误: {str(e)}"
    
    def _validate_proxy_format(self, proxy_url):
        """验证代理URL格式
        
        Args:
            proxy_url: 代理URL
            
        Returns:
            bool: 格式是否有效
        """
        import re
        # 检查格式是否为 http(s)://host:port
        pattern = r'^(http|https)://([a-zA-Z0-9.-]+)(:\d+)?$'
        return bool(re.match(pattern, proxy_url))
    
    def _analyze_proxy_error(self, error_msg):
        """分析代理错误并提供详细信息
        
        Args:
            error_msg: 错误信息
            
        Returns:
            str: 详细的错误分析
        """
        if "Connection refused" in error_msg:
            return "代理服务器拒绝连接，请检查代理服务器是否在线或端口是否正确"
        elif "Proxy Authentication Required" in error_msg:
            return "代理服务器需要认证，请在代理URL中包含用户名和密码，格式为 http(s)://user:pass@host:port"
        elif "Cannot connect to proxy" in error_msg:
            return "无法连接到代理服务器，请检查代理地址和端口是否正确"
        elif "Tunnel connection failed" in error_msg:
            return "隧道连接失败，代理服务器可能不支持HTTPS连接"
        else:
            return error_msg
    
    def _analyze_connection_error(self, error_msg):
        """分析连接错误并提供详细信息
        
        Args:
            error_msg: 错误信息
            
        Returns:
            str: 详细的错误分析
        """
        if "Name or service not known" in error_msg:
            return "无法解析代理服务器主机名，请检查代理地址是否正确"
        elif "Connection timed out" in error_msg:
            return "连接超时，代理服务器可能不在线或网络连接有问题"
        elif "No route to host" in error_msg:
            return "无法路由到主机，请检查网络连接和防火墙设置"
        else:
            return error_msg

    def get_system_proxy(self):
        """尝试获取系统代理设置
        
        Returns:
            (str, str): HTTP代理和HTTPS代理
        """
        http_proxy = os.environ.get('HTTP_PROXY', '')
        https_proxy = os.environ.get('HTTPS_PROXY', '')
        
        if not http_proxy and not https_proxy:
            # 尝试从Windows注册表获取代理设置
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
                    proxy_enabled, _ = winreg.QueryValueEx(key, 'ProxyEnable')
                    if proxy_enabled:
                        proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
                        if proxy_server:
                            if '://' not in proxy_server:
                                http_proxy = f'http://{proxy_server}'
                                https_proxy = f'https://{proxy_server}'
            except Exception as e:
                logger.warning(f"获取系统代理设置失败: {str(e)}")
        
        return http_proxy, https_proxy

    def auto_configure(self):
        """自动配置代理设置
        
        尝试检测系统代理设置并应用
        
        Returns:
            bool: 是否成功配置
        """
        http_proxy, https_proxy = self.get_system_proxy()
        
        if http_proxy or https_proxy:
            self.set_proxy_enabled(True)
            if http_proxy:
                self.set_http_proxy(http_proxy)
            if https_proxy:
                self.set_https_proxy(https_proxy)
            self.save_config()
            logger.info(f"已自动配置代理: HTTP={http_proxy}, HTTPS={https_proxy}")
            return True
        else:
            logger.info("未检测到系统代理设置")
            return False