import os
import time
import threading
import pytube
import subprocess
from pytube.exceptions import RegexMatchError, VideoUnavailable

class YouTubeDownloader:
    def __init__(self, download_path):
        self.download_path = download_path
        self.is_paused = False
        self.is_cancelled = False
        self.current_download = None
        self.lock = threading.Lock()
    
    def set_download_path(self, path):
        """设置下载路径"""
        self.download_path = path
    
    def download(self, url, quality="1080p", download_type="视频+音频", progress_callback=None):
        """下载YouTube视频
        
        Args:
            url: YouTube视频URL
            quality: 视频质量 (最高质量, 1080p, 720p, 480p, 360p)
            download_type: 下载类型 (视频+音频, 仅视频, 仅音频)
            progress_callback: 进度回调函数
        """
        self.is_cancelled = False
        self.is_paused = False
        
        try:
            # 创建YouTube对象
            yt = pytube.YouTube(url, on_progress_callback=self._on_progress)
            self.current_download = yt
            
            # 设置进度回调
            self._progress_callback = progress_callback
            self._downloaded_bytes = 0
            self._total_bytes = 0
            
            # 根据下载类型选择下载方式
            if download_type == "仅音频":
                return self._download_audio_only(yt)
            elif download_type == "仅视频":
                return self._download_video_only(yt, quality)
            else:  # 视频+音频
                return self._download_video_audio(yt, quality)
                
        except RegexMatchError:
            raise Exception("无效的YouTube链接")
        except VideoUnavailable:
            raise Exception("视频不可用")
        except Exception as e:
            raise Exception(f"下载失败: {str(e)}")
    
    def _download_audio_only(self, yt):
        """仅下载音频"""
        # 获取最高质量的音频流
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        if not audio_stream:
            raise Exception("找不到可用的音频流")
        
        # 下载音频
        self._total_bytes = audio_stream.filesize
        file_path = audio_stream.download(output_path=self.download_path)
        
        # 重命名为mp3
        base, _ = os.path.splitext(file_path)
        new_file_path = base + '.mp3'
        os.rename(file_path, new_file_path)
        
        return new_file_path
    
    def _download_video_only(self, yt, quality):
        """仅下载视频"""
        # 根据质量选择视频流
        video_stream = self._get_video_stream(yt, quality)
        if not video_stream:
            raise Exception(f"找不到{quality}质量的视频流")
        
        # 下载视频
        self._total_bytes = video_stream.filesize
        file_path = video_stream.download(output_path=self.download_path)
        
        return file_path
    
    def _download_video_audio(self, yt, quality):
        """下载视频和音频并合并"""
        # 获取视频流
        video_stream = self._get_video_stream(yt, quality)
        if not video_stream:
            raise Exception(f"找不到{quality}质量的视频流")
        
        # 获取音频流
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        if not audio_stream:
            raise Exception("找不到可用的音频流")
        
        # 计算总大小
        self._total_bytes = video_stream.filesize + audio_stream.filesize
        
        # 下载视频
        temp_video_path = os.path.join(self.download_path, f"temp_video_{int(time.time())}.mp4")
        video_stream.download(output_path=os.path.dirname(temp_video_path), filename=os.path.basename(temp_video_path))
        
        # 检查是否取消
        if self.is_cancelled:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            return None
        
        # 下载音频
        temp_audio_path = os.path.join(self.download_path, f"temp_audio_{int(time.time())}.mp4")
        audio_stream.download(output_path=os.path.dirname(temp_audio_path), filename=os.path.basename(temp_audio_path))
        
        # 检查是否取消
        if self.is_cancelled:
            for path in [temp_video_path, temp_audio_path]:
                if os.path.exists(path):
                    os.remove(path)
            return None
        
        # 合并视频和音频
        output_path = os.path.join(self.download_path, f"{yt.title}.mp4")
        output_path = self._sanitize_filename(output_path)
        
        try:
            self._merge_video_audio(temp_video_path, temp_audio_path, output_path)
        finally:
            # 清理临时文件
            for path in [temp_video_path, temp_audio_path]:
                if os.path.exists(path):
                    os.remove(path)
        
        return output_path
    
    def _get_video_stream(self, yt, quality):
        """根据质量获取视频流"""
        if quality == "最高质量":
            # 获取最高分辨率的视频流（无音频）
            return yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
        
        # 根据指定分辨率获取视频流
        resolution_map = {
            "1080p": "1080p",
            "720p": "720p",
            "480p": "480p",
            "360p": "360p"
        }
        
        target_resolution = resolution_map.get(quality, "720p")
        video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True, resolution=target_resolution).first()
        
        # 如果找不到指定分辨率，尝试找最接近的分辨率
        if not video_stream:
            video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
        
        return video_stream
    
    def _merge_video_audio(self, video_path, audio_path, output_path):
        """使用FFmpeg合并视频和音频"""
        try:
            # 检查FFmpeg是否可用
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise Exception("FFmpeg未安装，无法合并视频和音频")
        
        # 合并视频和音频
        cmd = [
            "ffmpeg", "-i", video_path, "-i", audio_path, 
            "-c:v", "copy", "-c:a", "aac", "-strict", "experimental",
            output_path, "-y"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"合并失败: {stderr.decode()}")
    
    def _on_progress(self, stream, chunk, bytes_remaining):
        """下载进度回调"""
        if self.is_cancelled:
            raise Exception("下载已取消")
        
        # 暂停下载
        while self.is_paused and not self.is_cancelled:
            time.sleep(0.1)
        
        if self.is_cancelled:
            raise Exception("下载已取消")
        
        # 计算进度
        with self.lock:
            self._downloaded_bytes = self._total_bytes - bytes_remaining
            progress = self._downloaded_bytes / self._total_bytes if self._total_bytes > 0 else 0
            
            # 调用进度回调
            if self._progress_callback:
                self._progress_callback(progress)
    
    def pause(self):
        """暂停下载"""
        self.is_paused = True
    
    def resume(self):
        """恢复下载"""
        self.is_paused = False
    
    def cancel(self):
        """取消下载"""
        self.is_cancelled = True
        self.is_paused = False
    
    def _sanitize_filename(self, filename):
        """清理文件名，移除非法字符"""
        # 替换Windows文件名中不允许的字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 限制文件名长度
        base_path, file_name = os.path.split(filename)
        name, ext = os.path.splitext(file_name)
        if len(name) > 200:  # Windows文件名长度限制为260字符，预留一些空间给路径和扩展名
            name = name[:200]
        
        return os.path.join(base_path, name + ext)