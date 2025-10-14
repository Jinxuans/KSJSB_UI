#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeaderKS - SO文件管理和加载器
优化的SO文件下载、更新和加载系统

新功能：自动依赖检测和安装
- 自动检测SO模块加载时缺失的Python依赖
- 自动安装常见依赖包（如aiohttp-socks等）
- 支持通过环境变量控制自动安装行为
- 提供详细的错误信息和安装建议

环境变量配置：
- LEADERKS_SERVER_URL=url                # 自定义服务器地址（可选）

使用示例：
1. 基本使用（自动安装依赖和更新）：
   python KSJSB_Launcher.py

2. 自定义服务器地址：
   export LEADERKS_SERVER_URL=http://your-server.com:port
   python KSJSB_Launcher.py

3. 程序化使用：
   from LeaderKS1.0 import LeaderKS, ServerConfig, UpdateConfig
   
   config = ServerConfig()
   update_config = UpdateConfig()  # 默认开启所有功能
   leader_ks = LeaderKS(config, update_config)
   exit_code = leader_ks.run("Kuaishou")
"""

import platform
import sys
import os
import subprocess
import shutil
import importlib.util
import requests
import hashlib
import json
import time
import asyncio
import logging
import functools
import re
try:
    # Python 3.8+ 的现代方式
    from importlib.metadata import distributions
except ImportError:
    # Python < 3.8 的向后兼容
    try:
        from importlib_metadata import distributions  # type: ignore
    except ImportError:
        # 最后回退到 pkg_resources（仅用于非常旧的环境）
        import pkg_resources  # type: ignore
        distributions = None
import marshal
import datetime
import threading
from typing import Optional, Tuple, Dict, Any, Union, Callable, List
from urllib.parse import urljoin
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

# 定义简洁的符号
class Symbols:
    """简洁符号集"""
    SUCCESS = '[√]'
    ERROR = '[×]'
    WARNING = '[!]'
    INFO = '[i]'
    PROCESSING = '[*]'
    ARROW = '->'

class CustomFormatter(logging.Formatter):
    """自定义日志格式化器"""
    
    def format(self, record):
        # 直接返回消息内容，不添加任何前缀
        return record.getMessage()

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(CustomFormatter())

# 文件处理器（简化格式）
file_handler = logging.FileHandler('leaderks.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.propagate = False

def get_terminal_width() -> int:
    """获取终端宽度，兼容移动端"""
    try:
        import shutil
        width = shutil.get_terminal_size().columns
        # 移动端通常宽度较小，给一些边距
        return max(40, min(width, 80))
    except Exception:
        # 默认适合移动端的宽度
        return 50

def print_banner():
    """打印简洁的启动信息"""
    print("快手极速版 - 模块加载器")
    print("版本: 3.0 | 智能依赖管理 | 跨平台兼容")

class TechnicalFormatter:
    """简洁的信息格式化器"""
    
    @staticmethod
    def format_system_info(title: str, info_dict: Dict[str, Any]) -> str:
        """简洁格式显示系统信息"""
        lines = [f"[{title}]"]
        
        for key, value in info_dict.items():
            display_value = str(value)
            # 截断过长的值
            if len(display_value) > 60:
                display_value = display_value[:57] + "..."
            lines.append(f"  {key}: {display_value}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_progress_bar(current: int, total: int, width: int = None, 
                          prefix: str = "", suffix: str = "") -> str:
        """生成简洁的进度条"""
        if total <= 0:
            return f"{prefix} 100%"
            
        percentage = int((current / total) * 100)
        
        # 简洁的百分比显示
        if suffix:
            return f"{prefix} {percentage}% {suffix}"
        else:
            return f"{prefix} {percentage}%"

def performance_monitor(func: Callable) -> Callable:
    """性能监控装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        
        # 开始执行标记
        logger.debug(f"执行 {func_name}()")
        
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            # 性能等级判断
            if elapsed_time < 0.1:
                perf_level = "极速"
            elif elapsed_time < 1.0:
                perf_level = "良好"
            else:
                perf_level = "较慢"
            
            logger.debug(f"{func_name}() 完成 ({perf_level}: {elapsed_time:.3f}s)")
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"{func_name}() 执行失败 ({elapsed_time:.3f}s)")
            logger.error(f"└─ 错误详情: {e}")
            raise
    return wrapper

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """智能重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            func_name = func.__name__
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"重试 {func_name}() [{attempt + 1}/{max_retries}]")
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"{func_name}() 第 {attempt + 1} 次尝试失败")
                        logger.warning(f"└─ 错误: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}")
                        logger.info(f"{delay:.1f}s 后重试...")
                        time.sleep(delay)
                    else:
                        logger.error(f"{func_name}() 所有 {max_retries} 次尝试均失败")
            raise last_exception
        return wrapper
    return decorator

@dataclass
class ServerConfig:
    """服务器配置"""
    base_url: str = 'http://154.12.60.33:2424'
    download_endpoint: str = '/api/system/download.php'
    check_update_endpoint: str = '/api/system/check_update.php'
    timeout: int = 30
    retry_times: int = 3
    chunk_size: int = 8192
    retry_delay: int = 2

@dataclass
class UpdateConfig:
    """更新配置"""
    auto_update: bool = True
    ask_confirmation: bool = False
    backup_old_files: bool = True
    delete_backup_after_success: bool = True
    auto_install_dependencies: bool = True  # 自动安装缺失依赖

@dataclass
class SystemInfo:
    """系统信息"""
    architecture: str
    python_version_tag: str
    platform_info: str
    python_version: str

class DependencyManager:
    """依赖管理类"""
    
    # 常见依赖包映射 - 从错误信息到包名的映射
    DEPENDENCY_MAPPING = {
        'aiohttp_socks': 'aiohttp-socks',
        'aiohttp_socks_proxy': 'aiohttp-socks',
        'aiohttp_proxy': 'aiohttp-proxy',
        'aiohttp': 'aiohttp',
        'asyncio': 'asyncio',  # 通常内置
        'requests': 'requests',
        'urllib3': 'urllib3',
        'certifi': 'certifi',
        'charset_normalizer': 'charset-normalizer',
        'idna': 'idna',
        'cryptography': 'cryptography',
        'pycryptodome': 'pycryptodome',
        'pycryptodomex': 'pycryptodomex',
        'lxml': 'lxml',
        'beautifulsoup4': 'beautifulsoup4',
        'selenium': 'selenium',
        'webdriver_manager': 'webdriver-manager',
        'fake_useragent': 'fake-useragent',
        'user_agents': 'user-agents',
        'pytz': 'pytz',
        'dateutil': 'python-dateutil',
        'PIL': 'Pillow',
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'matplotlib': 'matplotlib',
        'scipy': 'scipy',
        'sklearn': 'scikit-learn',
        'tensorflow': 'tensorflow',
        'torch': 'torch',
        'transformers': 'transformers',
        'openai': 'openai',
        'anthropic': 'anthropic',
        'google': 'google-cloud',
        'boto3': 'boto3',
        'azure': 'azure-sdk',
        'redis': 'redis',
        'pymongo': 'pymongo',
        'sqlalchemy': 'sqlalchemy',
        'psycopg2': 'psycopg2-binary',
        'mysql': 'mysql-connector-python',
        'sqlite3': 'sqlite3',  # 通常内置
        'json': 'json',  # 内置
        'base64': 'base64',  # 内置
        'hashlib': 'hashlib',  # 内置
        'hmac': 'hmac',  # 内置
        'uuid': 'uuid',  # 内置
        'datetime': 'datetime',  # 内置
        'time': 'time',  # 内置
        'os': 'os',  # 内置
        'sys': 'sys',  # 内置
        're': 're',  # 内置
        'math': 'math',  # 内置
        'random': 'random',  # 内置
        'collections': 'collections',  # 内置
        'itertools': 'itertools',  # 内置
        'functools': 'functools',  # 内置
        'operator': 'operator',  # 内置
        'copy': 'copy',  # 内置
        'pickle': 'pickle',  # 内置
        'shelve': 'shelve',  # 内置
        'dbm': 'dbm',  # 内置
        'zlib': 'zlib',  # 内置
        'gzip': 'gzip',  # 内置
        'bz2': 'bz2',  # 内置
        'lzma': 'lzma',  # 内置
        'zipfile': 'zipfile',  # 内置
        'tarfile': 'tarfile',  # 内置
        'csv': 'csv',  # 内置
        'configparser': 'configparser',  # 内置
        'argparse': 'argparse',  # 内置
        'getopt': 'getopt',  # 内置
        'logging': 'logging',  # 内置
        'warnings': 'warnings',  # 内置
        'contextlib': 'contextlib',  # 内置
        'abc': 'abc',  # 内置
        'atexit': 'atexit',  # 内置
        'traceback': 'traceback',  # 内置
        'gc': 'gc',  # 内置
        'inspect': 'inspect',  # 内置
        'site': 'site',  # 内置
        'sysconfig': 'sysconfig',  # 内置
        'platform': 'platform',  # 内置
        'subprocess': 'subprocess',  # 内置
        'threading': 'threading',  # 内置
        'multiprocessing': 'multiprocessing',  # 内置
        'concurrent': 'concurrent',  # 内置
        'queue': 'queue',  # 内置
        'sched': 'sched',  # 内置
        'socket': 'socket',  # 内置
        'ssl': 'ssl',  # 内置
        'select': 'select',  # 内置
        'selectors': 'selectors',  # 内置
        'signal': 'signal',  # 内置
        'mmap': 'mmap',  # 内置
        'ctypes': 'ctypes',  # 内置
        'struct': 'struct',  # 内置
        'codecs': 'codecs',  # 内置
        'unicodedata': 'unicodedata',  # 内置
        'stringprep': 'stringprep',  # 内置
        'readline': 'readline',  # 内置
        'rlcompleter': 'rlcompleter',  # 内置
        'cmd': 'cmd',  # 内置
        'shlex': 'shlex',  # 内置
        'tkinter': 'tkinter',  # 内置
        'turtle': 'turtle',  # 内置
        'pdb': 'pdb',  # 内置
        'profile': 'profile',  # 内置
        'pstats': 'pstats',  # 内置
        'timeit': 'timeit',  # 内置
        'trace': 'trace',  # 内置
        'faulthandler': 'faulthandler',  # 内置
        'tracemalloc': 'tracemalloc',  # 内置
        'distutils': 'distutils',  # 内置
        'ensurepip': 'ensurepip',  # 内置
        'venv': 'venv',  # 内置
        'zipapp': 'zipapp',  # 内置
        'runpy': 'runpy',  # 内置
        'importlib': 'importlib',  # 内置
        'pkgutil': 'pkgutil',  # 内置
        'modulefinder': 'modulefinder',  # 内置
        'runpy': 'runpy',  # 内置
        'pkg_resources': 'setuptools',
        'setuptools': 'setuptools',
        'pip': 'pip',
        'wheel': 'wheel',
    }
    
    def __init__(self):
        self.installed_packages = self._get_installed_packages()
    
    def _get_installed_packages(self) -> set:
        """获取已安装的包列表"""
        try:
            if distributions is not None:
                # 使用现代的 importlib.metadata
                installed_packages = {dist.metadata['name'].lower() for dist in distributions()}
                return installed_packages
            else:
                # 回退到 pkg_resources（仅用于旧版本 Python）
                installed_packages = {pkg.project_name.lower() for pkg in pkg_resources.working_set}
                return installed_packages
        except Exception as e:
            logger.warning(f"无法获取已安装包列表: {e}")
            return set()
    
    def extract_missing_dependency(self, error_message: str) -> Optional[str]:
        """从ImportError消息中提取缺失的依赖包名"""
        # 匹配 "No module named 'xxx'" 模式
        pattern = r"No module named ['\"]([^'\"]+)['\"]"
        match = re.search(pattern, error_message)
        
        if match:
            module_name = match.group(1)
            # 处理子模块，如 'aiohttp_socks.proxy' -> 'aiohttp_socks'
            if '.' in module_name:
                module_name = module_name.split('.')[0]
            return module_name
        
        return None
    
    def get_package_name(self, module_name: str) -> Optional[str]:
        """根据模块名获取对应的包名"""
        # 直接查找映射
        if module_name in self.DEPENDENCY_MAPPING:
            package_name = self.DEPENDENCY_MAPPING[module_name]
            # 跳过内置模块
            if package_name == module_name and module_name in sys.builtin_module_names:
                return None
            return package_name
        
        # 尝试一些常见的转换规则
        # 下划线转连字符
        if '_' in module_name:
            package_name = module_name.replace('_', '-')
            return package_name
        
        # 直接使用模块名
        return module_name
    
    def is_package_installed(self, package_name: str) -> bool:
        """检查包是否已安装（智能匹配包名）"""
        package_lower = package_name.lower()
        
        # 直接匹配
        if package_lower in self.installed_packages:
            return True
        
        # 尝试连字符转下划线
        underscore_name = package_lower.replace('-', '_')
        if underscore_name in self.installed_packages:
            return True
        
        # 尝试下划线转连字符  
        hyphen_name = package_lower.replace('_', '-')
        if hyphen_name in self.installed_packages:
            return True
            
        return False
    
    def install_package(self, package_name: str) -> bool:
        """安装指定的包"""
        try:
            logger.info(f"安装依赖包: {package_name}")
            
            # 使用pip安装
            cmd = [sys.executable, '-m', 'pip', 'install', package_name, '--upgrade', '-q']
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f"{package_name} ({elapsed_time:.1f}s)")
                
                # 更新已安装包列表 - 需要更新实际的包名，不是安装名
                # 对于aiohttp-socks这种情况，安装名是aiohttp-socks，但实际包名是aiohttp_socks
                actual_package_name = package_name.replace('-', '_').lower()
                self.installed_packages.add(actual_package_name)
                return True
            else:
                logger.error(f"{package_name} 安装失败")
                if result.stderr:
                    error_lines = result.stderr.strip().split('\n')
                    # 只显示最后几行关键错误信息
                    for line in error_lines[-2:]:
                        if line.strip():
                            logger.error(f"└─ {line.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"{package_name} 安装超时 (>5min)")
            return False
        except Exception as e:
            logger.error(f"{package_name} 安装异常: {e}")
            return False
    
    def auto_install_dependency(self, error_message: str) -> bool:
        """自动检测并安装缺失的依赖"""
        # 提取缺失的模块名
        module_name = self.extract_missing_dependency(error_message)
        if not module_name:
            return False
        
        # 获取对应的包名
        package_name = self.get_package_name(module_name)
        if not package_name:
            return False
        
        # 检查是否已安装
        if self.is_package_installed(package_name):
            return True
        
        # 尝试安装
        logger.info(f"缺失依赖: {module_name}")
        return self.install_package(package_name)
    
    def check_and_install_common_dependencies(self) -> bool:
        """检查并安装常见依赖（静默检查）"""
        common_deps = ['requests', 'aiohttp', 'aiohttp-socks']
        all_installed = True
        
        missing_deps = [dep for dep in common_deps if not self.is_package_installed(dep)]
        
        if missing_deps:
            logger.info(f"检查依赖包...")
            for dep in missing_deps:
                if not self.install_package(dep):
                    all_installed = False
        
        return all_installed
    
    def get_installation_help(self, module_name: str) -> str:
        """获取手动安装依赖的帮助信息"""
        package_name = self.get_package_name(module_name)
        if package_name:
            return f"请手动安装依赖: pip install {package_name}"
        else:
            return f"请检查模块 '{module_name}' 是否正确，或手动安装相关依赖"
    
    def suggest_alternative_packages(self, module_name: str) -> List[str]:
        """建议可能的替代包"""
        suggestions = []
        
        # 基于模块名建议可能的包
        if 'socks' in module_name.lower():
            suggestions.extend(['aiohttp-socks', 'requests[socks]', 'pysocks'])
        elif 'http' in module_name.lower():
            suggestions.extend(['aiohttp', 'requests', 'httpx'])
        elif 'proxy' in module_name.lower():
            suggestions.extend(['aiohttp-socks', 'requests[socks]', 'pysocks'])
        
        return suggestions

class FileManager:
    """文件管理类"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.version_file = self.base_dir / 'version.json'
    
    def get_version_info_path(self) -> Path:
        """获取版本信息文件路径"""
        return self.version_file
    
    def save_version_info(self, version_info: Dict[str, Any]) -> bool:
        """保存版本信息到本地文件"""
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)
            # logger.info(f"版本信息已保存: {version_info}")
            return True
        except Exception as e:
            # logger.error(f"保存版本信息失败: {e}")
            return False
    
    def load_version_info(self) -> Optional[Dict[str, Any]]:
        """从本地文件加载版本信息"""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载版本信息失败: {e}")
        return None
    
    def calculate_file_hash(self, file_path: Union[str, Path]) -> Optional[str]:
        """计算文件的MD5哈希值"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}")
            return None
    
    def backup_file(self, file_path: Path, suffix: str = '.backup') -> Optional[Path]:
        """备份文件"""
        try:
            backup_path = file_path.with_suffix(file_path.suffix + suffix)
            if backup_path.exists():
                backup_path.unlink()
            shutil.move(str(file_path), str(backup_path))
            logger.info(f"已备份文件: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份文件失败: {e}")
            return None
    
    def restore_file(self, backup_path: Path, original_path: Path) -> bool:
        """恢复文件"""
        try:
            shutil.move(str(backup_path), str(original_path))
            logger.info(f"已恢复文件: {original_path}")
            return True
        except Exception as e:
            logger.error(f"恢复文件失败: {e}")
            return False

class NetworkManager:
    """网络管理类"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LeaderKS/2.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _handle_api_response(self, response: requests.Response) -> Optional[Dict[str, Any]]:
        """处理API响应，使用统一的新格式"""
        try:
            result = response.json()
            
            # 检查新API统一响应格式
            if 'success' in result:
                if result.get('success'):
                    logger.debug(f"API响应成功: {result.get('message', '')}")
                    return result.get('data')
                else:
                    error_msg = result.get('message', '未知错误')
                    error_code = result.get('error_code')
                    logger.error(f"API错误: {error_msg}")
                    if error_code:
                        logger.error(f"错误代码: {error_code}")
                    return None
            else:
                # 兼容旧格式响应（临时处理）
                logger.debug("处理非标准API响应格式")
                return result
                
        except ValueError as e:
            logger.error(f"解析JSON响应失败: {e}")
            return None
        except Exception as e:
            logger.error(f"处理API响应时发生错误: {e}")
            return None
    
    @performance_monitor
    def check_server_update(self, base_name: str, py_ver_tag: str, 
                           arch: str, current_version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """检查服务器是否有更新版本"""
        try:
            url = urljoin(self.config.base_url, self.config.check_update_endpoint)
            data = {
                'base_name': base_name,
                'python_version': py_ver_tag,
                'architecture': arch,
                'current_version': current_version,
                'platform': platform.platform(),
                'os_type': 'windows' if is_windows() else 'linux',
                'file_type': 'pyc' if is_windows() else 'so'
            }
            
            response = self.session.post(url, json=data, timeout=self.config.timeout)
            response.raise_for_status()
            
            # 使用统一的响应处理
            return self._handle_api_response(response)
                
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                logger.error("❗ 服务器返回 404 错误 - 找不到请求的资源")
                logger.error("🔍 可能的原因:")
                logger.error("   1. 服务器上没有对应的文件版本")
                logger.error("   2. 您的系统架构或 Python 版本不受支持")
                logger.error("   3. 服务器配置问题")
                show_environment_info()
            else:
                logger.error(f"网络请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"检查更新时发生错误: {e}")
            return None
    
    def request_so_download(self, base_name: str, py_ver_tag: str, 
                           arch: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """向服务器请求文件下载链接"""
        try:
            url = urljoin(self.config.base_url, self.config.download_endpoint)
            data = {
                'base_name': base_name,
                'python_version': py_ver_tag,
                'architecture': arch,
                'platform': platform.platform(),
                'os_type': 'windows' if is_windows() else 'linux',
                'file_type': 'pyc' if is_windows() else 'so',
                'client_info': {
                    'python_version': sys.version,
                    'platform': platform.platform(),
                    'architecture': arch,
                    'os_type': 'windows' if is_windows() else 'linux',
                    'file_extension': get_file_extension()
                }
            }
            
            response = self.session.post(url, json=data, timeout=self.config.timeout)
            response.raise_for_status()
            
            # 使用统一的响应处理
            result = self._handle_api_response(response)
            
            if result:
                download_url = result.get('download_url')
                version_info = result.get('version_info', {})
                
                if download_url:
                    return download_url, version_info
                else:
                    logger.error("服务器未提供下载链接")
                    return None, None
            else:
                logger.error("获取下载信息失败")
                return None, None
                
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                logger.error("❗ 服务器返回 404 错误 - 找不到请求的资源")
                logger.error("🔍 可能的原因:")
                logger.error("   1. 服务器上没有对应的文件版本")
                logger.error("   2. 您的系统架构或 Python 版本不受支持")
                logger.error("   3. 服务器配置问题")
                show_environment_info()
            else:
                logger.error(f"网络请求失败: {e}")
            return None, None
        except Exception as e:
            logger.error(f"请求下载时发生错误: {e}")
            return None, None
    
    def download_so_file(self, base_name: str, py_ver_tag: str, 
                        arch: str, download_url: str) -> Optional[str]:
        """从服务器下载文件"""
        # 修正下载URL
        if download_url.startswith('http://154.12.60.33/') and ':2424' not in download_url:
            download_url = download_url.replace('http://154.12.60.33/', 'http://154.12.60.33:2424/')
        
        expected_filename = get_expected_filename(base_name, py_ver_tag, arch)
        temp_filename = f"{expected_filename}.tmp"
        
        for attempt in range(self.config.retry_times):
            try:
                response = self.session.get(
                    download_url, 
                    stream=True, 
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(temp_filename, 'wb') as f:
                    last_progress = -1
                    for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                progress = int((downloaded_size / total_size) * 100)
                                if progress != last_progress and progress % 5 == 0:  # 每5%更新一次
                                    # 计算下载速度
                                    current_time = time.time()
                                    if hasattr(self, '_download_start_time'):
                                        elapsed = current_time - self._download_start_time
                                        speed = downloaded_size / elapsed / 1024 / 1024  # MB/s
                                        speed_text = f"{speed:.1f} MB/s" if speed > 1 else f"{speed*1024:.1f} KB/s"
                                    else:
                                        self._download_start_time = current_time
                                        speed_text = "计算中..."
                                    
                                    # 格式化文件大小
                                    size_mb = downloaded_size / 1024 / 1024
                                    total_mb = total_size / 1024 / 1024
                                    
                                    # 简化进度显示
                                    progress_bar = TechnicalFormatter.format_progress_bar(
                                        downloaded_size, total_size,
                                        prefix="下载",
                                        suffix=f"{size_mb:.1f}MB"
                                    )
                                    print(f"\r{progress_bar}", end='', flush=True)
                                    last_progress = progress
                    
                    f.flush()
                    os.fsync(f.fileno())
                
                # 下载完成
                print(f"\r下载完成")
                print()  # 换行
                
                # 验证文件完整性
                if 'content-md5' in response.headers:
                    expected_hash = response.headers['content-md5']
                    actual_hash = self._calculate_temp_file_hash(temp_filename)
                    if expected_hash != actual_hash:
                        if attempt < self.config.retry_times - 1:
                            continue
                        else:
                            os.remove(temp_filename)
                            return None
                
                # 重命名为最终文件名
                os.rename(temp_filename, expected_filename)
                return os.path.abspath(expected_filename)
                
            except requests.exceptions.RequestException as e:
                self._cleanup_temp_file(temp_filename)
                if attempt < self.config.retry_times - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(f"下载失败: {e}")
                    return None
                    
            except Exception as e:
                self._cleanup_temp_file(temp_filename)
                if attempt < self.config.retry_times - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(f"下载错误: {e}")
                    return None
        
        return None
    
    def _calculate_temp_file_hash(self, temp_filename: str) -> Optional[str]:
        """计算临时文件的哈希值"""
        try:
            hash_md5 = hashlib.md5()
            with open(temp_filename, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算临时文件哈希失败: {e}")
            return None
    
    def _cleanup_temp_file(self, temp_filename: str):
        """清理临时文件"""
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

def is_windows() -> bool:
    """检测是否为 Windows 系统"""
    return platform.system().lower() == 'windows'

def get_file_extension() -> str:
    """根据操作系统获取文件扩展名"""
    return '.pyc' if is_windows() else '.so'

def get_expected_filename(base_name: str, py_ver_tag: str, arch: str) -> str:
    """生成平台特定的预期文件名"""
    if is_windows():
        return f"{base_name}.pyc"
    else:
        return f"{base_name}.cpython-{py_ver_tag}-{arch}-linux-gnu.so"

def show_environment_info():
    """显示详细的环境信息"""
    system_info = SystemInfoManager.get_system_info()
    expected_file = get_expected_filename("Kuaishou", system_info.python_version_tag, system_info.architecture)
    
    # 系统基础信息
    sys_info = {
        "操作系统": f"{platform.system()} {platform.release()}",
        "系统架构": platform.machine(),
        "Python版本": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "Python路径": sys.executable,
        "工作目录": os.getcwd(),
        "文件类型": get_file_extension(),
        "预期文件": expected_file
    }
    
    # 网络配置信息
    network_info = {
        "连接超时": "30秒",
        "重试次数": "3次",
        "块大小": "8KB"
    }
    
    print(TechnicalFormatter.format_system_info("系统环境", sys_info))
    print(TechnicalFormatter.format_system_info("网络配置", network_info))

class SystemInfoManager:
    """系统信息管理类"""
    
    @staticmethod
    def get_system_architecture() -> str:
        """获取当前系统的架构"""
        arch = platform.machine().lower()
        arch_mapping = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64',
            'aarch64': 'aarch64',
            'arm64': 'aarch64',
        }
        return arch_mapping.get(arch, arch)
    
    @staticmethod
    def get_python_version_tag() -> str:
        """获取与 .so 文件名兼容的 Python 版本标签"""
        major, minor = sys.version_info.major, sys.version_info.minor
        return f"{major}{minor}"
    
    @staticmethod
    def get_system_info() -> SystemInfo:
        """获取完整的系统信息"""
        return SystemInfo(
            architecture=SystemInfoManager.get_system_architecture(),
            python_version_tag=SystemInfoManager.get_python_version_tag(),
            platform_info=platform.platform(),
            python_version=sys.version
        )

def load_pyc_file(file_path: str, module_name: str) -> Optional[Any]:
    """加载 Windows .pyc 文件"""
    try:
        logger.info(f"尝试加载 .pyc 文件: {file_path}")
        
        with open(file_path, 'rb') as f:
            # 读取 .pyc 文件头
            magic = f.read(4)
            timestamp = f.read(4)
            size = f.read(4) if sys.version_info >= (3, 3) else b''
            
            # 读取代码对象
            code_data = f.read()
            
        # 反序列化代码对象
        code_obj = marshal.loads(code_data)
        
        # 创建模块并执行
        module = type(sys)(module_name)
        module.__file__ = file_path
        sys.modules[module_name] = module
        
        # 执行代码对象
        exec(code_obj, module.__dict__)
        
        logger.info(f"成功加载 .pyc 文件: {module_name}")
        return module
        
    except Exception as e:
        logger.error(f"加载 .pyc 文件失败: {e}")
        return None

def load_so_file(file_path: str, module_name: str) -> Optional[Any]:
    """加载 Linux .so 文件"""
    try:
        # logger.info(f"尝试加载 .so 文件: {file_path}")
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logger.error("无法创建模块规范")
            return None
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # logger.info(f"成功加载 .so 文件: {module_name}")
        return module
        
    except Exception as e:
        logger.error(f"加载 .so 文件失败: {e}")
        return None

def try_load_with_correct_name(file_path: str, module_name: str) -> Optional[Any]:
    """使用正确的加载方法加载文件"""
    if is_windows():
        return load_pyc_file(file_path, module_name)
    else:
        return load_so_file(file_path, module_name)

def check_so_dependencies(file_path: str) -> bool:
    """检查文件依赖（静默）"""
    if is_windows():
        # Windows 系统下 .pyc 文件不需要检查依赖
        return True
    
    try:
        # Linux 系统下检查 .so 文件依赖
        result = subprocess.run(['ldd', file_path], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
            
    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        return True  # 如果 ldd 不可用，假设依赖正常
    except Exception as e:
        return False

class SOModuleLoader:
    """SO模块加载器"""
    
    def __init__(self, file_manager: FileManager, dependency_manager: Optional[DependencyManager] = None):
        self.file_manager = file_manager
        self.dependency_manager = dependency_manager or DependencyManager()
        self.max_dependency_retries = 3  # 最大依赖安装重试次数
    
    def find_so_file(self, base_name: str, py_ver_tag: str, 
                     arch: str, auto_download: bool = True,
                     network_manager: Optional[NetworkManager] = None) -> Optional[str]:
        """查找文件，如果不存在则尝试下载"""
        expected_filename = get_expected_filename(base_name, py_ver_tag, arch)
        full_path = Path(expected_filename).resolve()
        
        if full_path.is_file():
            logger.info(f"找到本地文件: {expected_filename}")
            
            # 检查文件依赖（静默）
            check_so_dependencies(str(full_path))
            
            if auto_download and network_manager:
                return self._handle_update_check(base_name, py_ver_tag, arch, full_path, network_manager)
            
            return str(full_path)
        else:
            logger.info(f"本地文件不存在，从服务器获取...")
            
            if auto_download and network_manager:
                return self._handle_download(base_name, py_ver_tag, arch, network_manager)
            
            return None
    
    def _handle_update_check(self, base_name: str, py_ver_tag: str, arch: str,
                           full_path: Path, network_manager: NetworkManager) -> str:
        """处理更新检查"""
        current_version_info = self.file_manager.load_version_info()
        current_version = current_version_info.get('version') if current_version_info else None
        
        update_info = network_manager.check_server_update(base_name, py_ver_tag, arch, current_version)
        
        if update_info and update_info.get('has_update'):
            logger.info(f"发现新版本: {update_info.get('latest_version')}")
            description = update_info.get('update_description', '无更新说明')
            if description != '无更新说明':
                logger.info(f"更新内容: {description}")
            
            return self._perform_update(base_name, py_ver_tag, arch, full_path, network_manager)
        
        return str(full_path)
    
    def _handle_download(self, base_name: str, py_ver_tag: str, arch: str,
                        network_manager: NetworkManager) -> Optional[str]:
        """处理下载"""
        logger.info(f"准备下载模块文件...")
        
        current_version_info = self.file_manager.load_version_info()
        current_version = current_version_info.get('version') if current_version_info else None
        
        update_info = network_manager.check_server_update(base_name, py_ver_tag, arch, current_version)
        download_url, version_info = network_manager.request_so_download(base_name, py_ver_tag, arch)
        
        if download_url:
            downloaded_path = network_manager.download_so_file(base_name, py_ver_tag, arch, download_url)
            
            if downloaded_path and Path(downloaded_path).is_file():
                if version_info:
                    self.file_manager.save_version_info(version_info)
                logger.info(f"模块下载完成")
                return downloaded_path
            else:
                logger.error(f"下载过程中发生错误")
        else:
            logger.error(f"无法获取下载链接")
        
        return None
    
    def _perform_update(self, base_name: str, py_ver_tag: str, arch: str,
                       full_path: Path, network_manager: NetworkManager) -> str:
        """执行更新"""
        logger.info(f"正在更新模块...")
        download_url, version_info = network_manager.request_so_download(base_name, py_ver_tag, arch)
        
        if download_url:
            # 备份旧文件
            backup_filename = None
            if hasattr(self, 'update_config') and self.update_config.backup_old_files:
                backup_filename = self.file_manager.backup_file(full_path)
                if backup_filename:
                    logger.info(f"已备份旧文件")
            
            # 下载新文件
            downloaded_path = network_manager.download_so_file(base_name, py_ver_tag, arch, download_url)
            
            if downloaded_path and Path(downloaded_path).is_file():
                logger.info(f"模块更新完成")
                
                if version_info:
                    self.file_manager.save_version_info(version_info)
                
                # 删除备份文件
                if backup_filename and hasattr(self, 'update_config') and self.update_config.delete_backup_after_success:
                    if backup_filename.exists():
                        backup_filename.unlink()
                        logger.info(f"已清理备份文件")
                
                return downloaded_path
            else:
                logger.error(f"更新失败")
                if backup_filename:
                    self.file_manager.restore_file(backup_filename, full_path)
                    logger.info(f"已恢复原文件")
                return str(full_path)
        else:
            logger.error(f"无法获取更新链接")
            return str(full_path)
    
    def _list_so_files(self):
        """列出当前目录下的文件"""
        file_ext = get_file_extension()
        logger.info(f"当前目录下的 {file_ext} 文件:")
        try:
            pattern = f'*{file_ext}'
            for f in Path('.').glob(pattern):
                logger.info(f"  - {f}")
        except Exception as e:
            logger.error(f"无法列出 {file_ext} 文件: {e}")
    
    def load_module(self, file_path: str, module_name: str) -> Optional[Any]:
        """加载模块，自动处理缺失依赖"""
        # 检查是否启用自动依赖安装
        auto_install = getattr(self, 'update_config', None) and getattr(self.update_config, 'auto_install_dependencies', True)
        
        for attempt in range(self.max_dependency_retries + 1):
            try:
                # 使用正确的加载方法
                module = try_load_with_correct_name(file_path, module_name)
                if module:
                    # logger.info(f"模块加载成功")
                    return module
                else:
                    logger.error(f"模块加载失败")
                    return None
                
            except ImportError as e:
                error_msg = str(e)
                
                # 尝试自动安装缺失的依赖
                if auto_install and attempt < self.max_dependency_retries:
                    if self.dependency_manager.auto_install_dependency(error_msg):
                        continue
                    else:
                        continue
                else:
                    if not auto_install:
                        module_name = self.dependency_manager.extract_missing_dependency(error_msg)
                        if module_name:
                            help_msg = self.dependency_manager.get_installation_help(module_name)
                            logger.error(f"缺失依赖: {module_name}")
                            logger.info(f"建议: {help_msg}")
                    else:
                        logger.error(f"依赖安装失败")
                    return None
                    
            except Exception as e:
                logger.error(f"模块加载异常: {e}")
                return None
        
        return None
    
    def call_function(self, module: Any, function_name: str = "main", 
                     args_list: Optional[list] = None) -> Optional[Any]:
        """调用模块中的函数"""
        try:
            if hasattr(module, function_name):
                target_func = getattr(module, function_name)
                
                if args_list is None:
                    if asyncio.iscoroutinefunction(target_func):
                        result = asyncio.run(target_func())
                    else:
                        result = target_func()
                else:
                    if asyncio.iscoroutinefunction(target_func):
                        result = asyncio.run(target_func(*args_list))
                    else:
                        result = target_func(*args_list)
                
                return result
            else:
                logger.error(f"未找到函数 '{function_name}'")
                attrs = [attr for attr in dir(module) if not attr.startswith('_') and callable(getattr(module, attr, None))]
                if attrs:
                    logger.info(f"可用函数:")
                    for attr in sorted(attrs):
                        logger.info(f"  - {attr}")
                return None

        except Exception as e:
            logger.error(f"函数调用异常: {e}")
            return None

class LeaderKS:
    """主控制器类"""
    
    def __init__(self, config: ServerConfig, update_config: UpdateConfig):
        self._init_time = time.time()  # 记录初始化时间
        self.config = config
        self.update_config = update_config
        self.file_manager = FileManager()
        self.network_manager = NetworkManager(config)
        self.system_info = SystemInfoManager.get_system_info()
        self.dependency_manager = DependencyManager()
        self.so_loader = SOModuleLoader(self.file_manager, self.dependency_manager)
        self.so_loader.update_config = update_config
        
        # 验证配置
        self._validate_config()
    
    def _get_memory_usage(self) -> float:
        """获取当前进程的内存使用量（MB）"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # 转换为 MB
        except ImportError:
            # 如果没有 psutil，使用简单的方法
            try:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                # 在 Linux 上 ru_maxrss 是 KB，在 macOS 上是 bytes
                if platform.system().lower() == 'darwin':  # macOS
                    return usage.ru_maxrss / 1024 / 1024  # bytes -> MB
                else:  # Linux
                    return usage.ru_maxrss / 1024  # KB -> MB
            except Exception:
                return 0.0
    
    def _validate_config(self):
        """验证配置的有效性"""
        try:
            # 验证服务器配置
            if not self.config.base_url.startswith(('http://', 'https://')):
                logger.warning("服务器地址格式可能不正确")
            
            if self.config.timeout <= 0:
                logger.warning("超时时间应该大于0")
                self.config.timeout = 30
            
            if self.config.retry_times <= 0:
                logger.warning("重试次数应该大于0")
                self.config.retry_times = 3
            
            # 验证更新配置
            if self.update_config.auto_update and not self.update_config.backup_old_files:
                logger.warning("自动更新时建议启用文件备份")
                
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
    
    def diagnose_environment(self):
        """诊断运行环境"""
        # logger.info(f"正在进行系统环境诊断...")
        
        # 系统信息
        sys_info = {
            "Python版本": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "平台信息": self.system_info.platform_info,
            "系统架构": self.system_info.architecture
        }
        

        
        print(TechnicalFormatter.format_system_info("运行环境", sys_info))
        
        # 静默检查依赖
        logger.info(f"检查系统依赖...")
        
        # 性能统计
        # perf_info = {
        #     "内存使用": f"{self._get_memory_usage():.1f} MB",
        #     "CPU核心": f"{os.cpu_count()} 核",
        #     "启动时间": f"{time.time() - getattr(self, '_init_time', time.time()):.2f}s"
        # }
        # print(TechnicalFormatter.format_system_info("性能指标", perf_info))
        
        self._check_dependencies()
        self.dependency_manager.check_and_install_common_dependencies()
    
    def _check_dependencies(self):
        """检查关键依赖（静默检查）"""
        try:
            import requests
            # 静默检查成功
        except ImportError:
            logger.error("✗ requests 依赖未安装")
        
        try:
            import asyncio
            # 静默检查成功
        except ImportError:
            logger.error("✗ asyncio 依赖不可用")
    
    def run(self, so_base_name: str = "Kuaishou", custom_args: Optional[list] = None) -> int:
        """运行主程序"""
        start_time = time.time()
        
        try:
            # 打印启动横幅
            print_banner()
            # logger.info(f"启动 LeaderKS 模块加载引擎")
            
            # 1. 环境诊断
            self.diagnose_environment()
            
            # 2. 查找SO文件
            # logger.info(f"查找模块文件: {so_base_name}")
            so_file_path = self.so_loader.find_so_file(
                so_base_name, 
                self.system_info.python_version_tag, 
                self.system_info.architecture, 
                auto_download=self.update_config.auto_update,
                network_manager=self.network_manager
            )
            
            if not so_file_path:
                logger.error(f"找不到 {get_file_extension()} 文件")
                logger.error(f"└─ 可能原因: 服务器无对应版本、网络问题或本地文件缺失")
                return 1
            
            # 3. 尝试加载模块
            logger.info(f"加载模块...")
            module = self._load_module_with_fallback(so_file_path, so_base_name)
            if module is None:
                logger.error(f"模块加载失败")
                logger.error(f"└─ 可能原因: 文件损坏、依赖缺失或版本不兼容")
                return 2
            
            # 4. 调用函数
            # logger.info(f"执行主函数...")
            exit_code = self.so_loader.call_function(module, "main", custom_args)
            
            elapsed_time = time.time() - start_time
            
            # 执行完成状态
            if exit_code == 0 or exit_code is None:
                logger.info(f"执行完成 (总耗时: {elapsed_time:.1f}s)")
                return 0
            else:
                logger.warning(f"执行完成但返回非零代码: {exit_code} (耗时: {elapsed_time:.1f}s)")
                return exit_code
                
        except KeyboardInterrupt:
            logger.warning(f"程序被用户中断")
            return 130
        except Exception as e:
            logger.error(f"运行时异常: {e}")
            return 1
    
    def _load_module_with_fallback(self, so_file_path: str, so_base_name: str) -> Optional[Any]:
        """使用多种方法尝试加载模块"""
        # 方法一：使用基础名称
        module = self.so_loader.load_module(so_file_path, so_base_name)
        
        # 方法二：尝试其他可能的模块名
        if module is None:
            possible_names = [
                "Kuaishou",  # 首字母大写
                "kuaishou",  # 全小写
                so_base_name.lower(),
            ]
            
            for name in possible_names:
                if module is None and name != so_base_name:
                    module = self.so_loader.load_module(so_file_path, name)
                    if module:
                        break
        
        return module

def create_default_config() -> Tuple[ServerConfig, UpdateConfig]:
    """创建默认配置"""
    server_config = ServerConfig()
    update_config = UpdateConfig()
    
    # 检查服务器URL环境变量
    if os.getenv('LEADERKS_SERVER_URL'):
        server_config.base_url = os.getenv('LEADERKS_SERVER_URL')
        logger.info(f"使用自定义服务器地址: {server_config.base_url}")
    
    # 直接开启自动更新和自动依赖安装
    update_config.auto_update = True
    update_config.auto_install_dependencies = True
    
    return server_config, update_config

def main():
    """主函数"""
    try:
        # 创建配置
        server_config, update_config = create_default_config()
        
        # 创建主控制器
        leader_ks = LeaderKS(server_config, update_config)
        
        # 运行程序
        exit_code = leader_ks.run("Kuaishou")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"程序启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()