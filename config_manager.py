import os
import configparser
import tempfile

class ConfigManager:
    def __init__(self, config_file="config.ini"):
        """初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)
        self.config = configparser.ConfigParser()
        
        # 创建默认配置
        self._create_default_config()
        
        # 加载配置
        self.load_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        if not os.path.exists(self.config_file):
            # 使用更可靠的路径解析方式
            try:
                # 首先尝试使用当前目录
                default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
            except:
                # 如果失败，使用临时目录
                default_path = os.path.join(tempfile.gettempdir(), "YouTubeDownloader")
            
            self.config["General"] = {
                "DownloadPath": default_path
            }
            self.config["Settings"] = {
                "DefaultQuality": "1080p",
                "DefaultType": "视频+音频",
                "MaxConcurrentDownloads": "10"
            }
            self.save_config()
    
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding="utf-8")
    
    def save_config(self):
        """保存配置"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)
    
    def get_download_path(self):
        """获取下载路径"""
        return self.config.get("General", "DownloadPath")
    
    def set_download_path(self, path):
        """设置下载路径"""
        self.config["General"]["DownloadPath"] = path
        self.save_config()
    
    def get_default_quality(self):
        """获取默认视频质量"""
        return self.config.get("Settings", "DefaultQuality")
    
    def set_default_quality(self, quality):
        """设置默认视频质量"""
        self.config["Settings"]["DefaultQuality"] = quality
        self.save_config()
    
    def get_default_type(self):
        """获取默认下载类型"""
        return self.config.get("Settings", "DefaultType")
    
    def set_default_type(self, download_type):
        """设置默认下载类型"""
        self.config["Settings"]["DefaultType"] = download_type
        self.save_config()
    
    def get_max_concurrent_downloads(self):
        """获取最大并发下载数"""
        return int(self.config.get("Settings", "MaxConcurrentDownloads"))
    
    def set_max_concurrent_downloads(self, count):
        """设置最大并发下载数"""
        self.config["Settings"]["MaxConcurrentDownloads"] = str(count)
        self.save_config()