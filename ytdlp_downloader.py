#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YouTube批量下载工具 - yt-dlp下载器

这个模块使用yt-dlp库实现YouTube视频下载功能，
相比pytube提供更可靠的下载体验和更好的错误处理。
"""

import os
import time
import threading
import subprocess
import logging
import random
import yt_dlp
import concurrent.futures
from queue import Queue

# 尝试导入代理管理器
try:
    from proxy_manager import ProxyManager
    has_proxy_manager = True
except ImportError:
    has_proxy_manager = False

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ytdlp_downloader')

class YtdlpDownloader:
    """基于yt-dlp的YouTube下载器"""
    
    def __init__(self, download_path):
        self.download_path = download_path
        self.is_paused = False
        self.is_cancelled = False
        self.current_download = None
        self.lock = threading.Lock()
        self.max_retries = 3  # 最大重试次数
        self.max_workers = 3  # 最大并发下载数，可根据需要调整
        
        # 初始化代理管理器
        self.proxy_manager = ProxyManager() if has_proxy_manager else None
        
        # 创建下载目录
        os.makedirs(self.download_path, exist_ok=True)
    
    def set_download_path(self, path):
        """设置下载路径"""
        self.download_path = path
        os.makedirs(self.download_path, exist_ok=True)
    
    def set_proxy(self, proxy_url=None):
        """设置HTTP代理"""
        self.proxy = proxy_url
    
    def download(self, url, quality="1080p", download_type="视频+音频", progress_callback=None, use_proxy=None):
        """下载YouTube视频
        
        Args:
            url: YouTube视频URL
            quality: 视频质量 (最高质量, 1080p, 720p, 480p, 360p)
            download_type: 下载类型 (视频+音频, 仅视频, 仅音频)
            progress_callback: 进度回调函数
            use_proxy: 是否使用代理，None表示使用当前设置，True强制使用，False强制不使用
        """
        self.is_cancelled = False
        self.is_paused = False
        
        # 设置进度回调
        self._progress_callback = progress_callback
        self._downloaded_bytes = 0
        self._total_bytes = 0
        
        # 应用代理设置
        proxy = None
        if self.proxy_manager:
            if use_proxy is not None:
                self.proxy_manager.set_proxy_enabled(use_proxy)
            
            if self.proxy_manager.is_proxy_enabled():
                http_proxy = self.proxy_manager.get_http_proxy()
                https_proxy = self.proxy_manager.get_https_proxy()
                proxy = https_proxy or http_proxy
                logger.info(f"使用代理下载: {proxy}")
            else:
                logger.info("不使用代理下载")
        
        # 添加重试机制
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                # 如果是重试，添加随机延迟避免频繁请求
                if retry_count > 0:
                    delay = random.uniform(1, 3) * retry_count
                    logger.info(f"重试前等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                    
                    # 提供详细的重试信息
                    if progress_callback:
                        progress_callback(0, f"重试下载 ({retry_count}/{self.max_retries})...")
                
                # 根据下载类型选择下载方式
                if download_type == "仅音频":
                    return self._download_audio_only(url, proxy)
                elif download_type == "仅视频":
                    return self._download_video_only(url, quality, proxy)
                else:  # 视频+音频
                    return self._download_video_audio(url, quality, proxy)
                    
            except Exception as e:
                last_error = e
                logger.error(f"下载错误: {str(e)} - 重试 {retry_count+1}/{self.max_retries}")
                retry_count += 1
        
        # 如果所有重试都失败
        error_type = type(last_error).__name__
        error_msg = str(last_error)
        detailed_msg = f"下载失败 ({error_type}): {error_msg}"
        logger.error(detailed_msg)
        raise Exception(detailed_msg)
    
    def _get_ydl_opts(self, proxy=None):
        """获取yt-dlp基本选项"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'nocheckcertificate': True,
            'noprogress': True,
            'noplaylist': True,
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
        }
        
        # 添加代理设置
        if proxy:
            ydl_opts['proxy'] = proxy
        
        return ydl_opts
    
    def _download_audio_only(self, url, proxy=None):
        """仅下载音频"""
        ydl_opts = self._get_ydl_opts(proxy)
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            self._total_bytes = info.get('filesize') or 0
            if self._progress_callback:
                self._progress_callback(0, "准备下载音频...")
            
            # 检查是否取消
            if self.is_cancelled:
                return None
            
            # 下载音频
            ydl.download([url])
            
            # 获取下载后的文件路径
            title = info.get('title', 'video')
            file_path = os.path.join(self.download_path, f"{title}.mp3")
            return file_path
    
    def _download_video_only(self, url, quality, proxy=None):
        """仅下载视频"""
        # 根据质量选择格式
        format_code = self._get_format_code(quality, video_only=True)
        
        ydl_opts = self._get_ydl_opts(proxy)
        ydl_opts.update({
            'format': format_code,
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            self._total_bytes = info.get('filesize') or 0
            if self._progress_callback:
                self._progress_callback(0, "准备下载视频...")
            
            # 检查是否取消
            if self.is_cancelled:
                return None
            
            # 下载视频
            ydl.download([url])
            
            # 获取下载后的文件路径
            title = info.get('title', 'video')
            ext = info.get('ext', 'mp4')
            file_path = os.path.join(self.download_path, f"{title}.{ext}")
            return file_path
    
    def _download_video_audio(self, url, quality, proxy=None):
        """下载视频和音频"""
        # 根据质量选择格式
        format_code = self._get_format_code(quality)
        
        ydl_opts = self._get_ydl_opts(proxy)
        ydl_opts.update({
            'format': format_code,
            'merge_output_format': 'mp4',
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            self._total_bytes = info.get('filesize') or 0
            if self._progress_callback:
                self._progress_callback(0, "准备下载视频...")
            
            # 检查是否取消
            if self.is_cancelled:
                return None
            
            # 下载视频
            ydl.download([url])
            
            # 获取下载后的文件路径
            title = info.get('title', 'video')
            file_path = os.path.join(self.download_path, f"{title}.mp4")
            return file_path
    
    def _get_format_code(self, quality, video_only=False):
        """根据质量获取格式代码"""
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
                return "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
    
    def _progress_hook(self, d):
        """下载进度回调"""
        if self.is_cancelled:
            raise Exception("下载已取消")
        
        # 暂停下载
        while self.is_paused and not self.is_cancelled:
            time.sleep(0.1)
        
        if self.is_cancelled:
            raise Exception("下载已取消")
        
        # 计算进度
        if d['status'] == 'downloading':
            # 获取下载进度
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            
            if total > 0:
                with self.lock:
                    self._downloaded_bytes = downloaded
                    self._total_bytes = total
                    progress = downloaded / total
                    
                    # 调用进度回调
                    if self._progress_callback:
                        self._progress_callback(progress, f"下载中: {d.get('_percent_str', '0%')}")
        
        elif d['status'] == 'finished':
            if self._progress_callback:
                self._progress_callback(1.0, "下载完成，正在处理...")
    
    def pause(self):
        """暂停下载"""
        self.is_paused = True
        logger.info("下载已暂停")
    
    def resume(self):
        """继续下载"""
        self.is_paused = False
        logger.info("下载已继续")
    
    def cancel(self):
        """取消下载"""
        self.is_cancelled = True
        logger.info("下载已取消")
    
    def check_ffmpeg(self):
        """检查FFmpeg是否已安装"""
        try:
            subprocess.check_call(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    # 在_get_format_string方法中添加对2K和4K的支持
    def _get_format_string(self, resolution=None):
        """根据分辨率获取格式字符串"""
        if not resolution or resolution == "最佳质量":
            # 默认获取最佳质量
            return "bestvideo+bestaudio/best"
        elif resolution == "仅音频":
            return "bestaudio/best"
        
        # 根据分辨率选择格式
        if resolution == "1080p":
            return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        elif resolution == "720p":
            return "bestvideo[height<=720]+bestaudio/best[height<=720]"
        elif resolution == "480p":
            return "bestvideo[height<=480]+bestaudio/best[height<=480]"
        elif resolution == "360p":
            return "bestvideo[height<=360]+bestaudio/best[height<=360]"
        elif resolution == "240p":
            return "bestvideo[height<=240]+bestaudio/best[height<=240]"
        elif resolution == "2K":
            # 对于2K视频 (1440p)
            return "bestvideo[height<=1440]+bestaudio/best[height<=1440]"
        elif resolution == "4K":
            # 对于4K视频 (2160p)
            return "bestvideo[height<=2160]+bestaudio/best[height<=2160]"
        else:
            # 默认获取最佳质量
            return "bestvideo+bestaudio/best"
    
    def start_concurrent_downloads(self, urls, quality="1080p", download_type="视频+音频", progress_callback=None):
        """启动并发下载"""
        def single_progress_callback(progress, status_text=None, url=None):
            # 包装进度回调，带上url
            if progress_callback:
                progress_callback(progress, status_text, url)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(
                    self.download, url, quality, download_type,
                    lambda p, s=None, u=url: single_progress_callback(p, s, u)
                ): url for url in urls
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    future.result()
                except Exception as exc:
                    if progress_callback:
                        progress_callback(0, f"下载失败: {exc}", url)
                else:
                    if progress_callback:
                        progress_callback(100, "下载完成", url)