#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手极速版Web管理界面 - 后端服务
"""

import os
import json
import subprocess
import threading
import time
import queue
import signal
import sys
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kuaishou_web_secret_key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量
script_process = None
log_queue = queue.Queue()
is_running = False

# 文件路径
ACCOUNTS_FILE = 'accounts.json'
CONFIG_FILE = 'config.json'
SCRIPT_FILE = 'KSJSB_Launcher.py'

class LogHandler:
    """日志处理器"""
    
    def __init__(self, process, socketio):
        self.process = process
        self.socketio = socketio
        self.running = True
        
    def start_monitoring(self):
        """开始监控日志输出"""
        threading.Thread(target=self._monitor_stdout, daemon=True).start()
        threading.Thread(target=self._monitor_stderr, daemon=True).start()
        
    def _monitor_stdout(self):
        """监控标准输出"""
        try:
            import select
            import sys
            
            # 发送启动日志
            self.socketio.emit('log', {
                'type': 'log',
                'message': '🚀 脚本已启动，开始执行...',
                'timestamp': time.time()
            })
            
            while self.running and self.process.poll() is None:
                try:
                    # 使用非阻塞读取
                    if sys.platform == 'win32':
                        # Windows下的处理
                        import msvcrt
                        import os
                        if self.process.stdout:
                            line = self.process.stdout.readline()
                            if line:
                                # 尝试多种编码方式解码
                                log_message = None
                                for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
                                    try:
                                        log_message = line.decode(encoding).strip()
                                        break
                                    except UnicodeDecodeError:
                                        continue
                                
                                if not log_message:
                                    log_message = line.decode('utf-8', errors='replace').strip()
                                
                                if log_message:
                                    print(f"[LOG] {log_message}")  # 同时输出到控制台
                                    self.socketio.emit('log', {
                                        'type': 'log',
                                        'message': log_message,
                                        'timestamp': time.time()
                                    })
                    else:
                        # Linux/Mac下的处理
                        line = self.process.stdout.readline()
                        if line:
                            # 尝试多种编码方式解码
                            log_message = None
                            for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
                                try:
                                    log_message = line.decode(encoding).strip()
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if not log_message:
                                log_message = line.decode('utf-8', errors='replace').strip()
                            
                            if log_message:
                                print(f"[LOG] {log_message}")  # 同时输出到控制台
                                self.socketio.emit('log', {
                                    'type': 'log',
                                    'message': log_message,
                                    'timestamp': time.time()
                                })
                except Exception as e:
                    print(f"读取stdout出错: {e}")
                
                time.sleep(0.1)
        except Exception as e:
            print(f"监控stdout出错: {e}")
            self.socketio.emit('log', {
                'type': 'log',
                'message': f'❌ 日志监控异常: {str(e)}',
                'timestamp': time.time()
            })
            
    def _monitor_stderr(self):
        """监控错误输出"""
        # 由于我们已经将stderr合并到stdout，这个方法不再需要
        pass
            
    def stop(self):
        """停止监控"""
        self.running = False
        
        # 确保读取剩余的缓冲区内容
        try:
            if self.process and self.process.stdout:
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    
                    # 尝试多种编码方式解码
                    log_message = None
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
                        try:
                            log_message = line.decode(encoding).strip()
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if not log_message:
                        log_message = line.decode('utf-8', errors='replace').strip()
                    
                    if log_message:
                        print(f"[LOG] {log_message}")
                        self.socketio.emit('log', {
                            'type': 'log',
                            'message': log_message,
                            'timestamp': time.time()
                        })
        except Exception as e:
            print(f"停止监控时读取剩余内容出错: {e}")

def load_json_file(filepath, default=None):
    """加载JSON文件"""
    if default is None:
        default = []
    
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return default
    except Exception as e:
        print(f"加载文件 {filepath} 失败: {e}")
        return default

def save_json_file(filepath, data):
    """保存JSON文件"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存文件 {filepath} 失败: {e}")
        return False

@app.route('/')
def index():
    """主页面 - 重定向到远端服务器"""
    return redirect('http://154.12.60.33:2424/', code=302)

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """获取账号列表"""
    try:
        accounts = load_json_file(ACCOUNTS_FILE, [])
        return jsonify(accounts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts', methods=['POST'])
def save_accounts():
    """保存账号列表"""
    try:
        accounts = request.json
        if not isinstance(accounts, list):
            return jsonify({'error': '账号数据必须是数组格式'}), 400
        
        # 验证账号数据格式
        for i, account in enumerate(accounts):
            if not isinstance(account, dict):
                return jsonify({'error': f'第{i+1}个账号数据格式错误'}), 400
            if 'salt' not in account or 'cookie' not in account:
                return jsonify({'error': f'第{i+1}个账号缺少必要字段'}), 400
        
        if save_json_file(ACCOUNTS_FILE, accounts):
            return jsonify({'success': True})
        else:
            return jsonify({'error': '保存账号文件失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    try:
        config = load_json_file(CONFIG_FILE, {})
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """保存配置"""
    try:
        config = request.json
        if not isinstance(config, dict):
            return jsonify({'error': '配置数据必须是对象格式'}), 400
        
        if save_json_file(CONFIG_FILE, config):
            return jsonify({'success': True})
        else:
            return jsonify({'error': '保存配置文件失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test', methods=['POST'])
def test_script():
    """运行测试脚本"""
    global script_process, is_running
    
    try:
        if is_running:
            return jsonify({'error': '脚本正在运行中'}), 400
        
        # 使用测试脚本
        test_script_file = 'test_log.py'
        if not os.path.exists(test_script_file):
            return jsonify({'error': f'测试脚本文件 {test_script_file} 不存在'}), 404
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        if os.name == 'nt':  # Windows
            env['CHCP'] = '65001'  # UTF-8编码页
        
        # 启动测试脚本
        script_process = subprocess.Popen(
            ['python', '-u', test_script_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=os.getcwd(),
            bufsize=0,
            universal_newlines=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        is_running = True
        
        # 启动日志监控
        log_handler = LogHandler(script_process, socketio)
        log_handler.start_monitoring()
        
        # 启动进程监控线程
        threading.Thread(target=monitor_process, args=(script_process, log_handler), daemon=True).start()
        
        socketio.emit('status', {
            'type': 'status',
            'status': '运行中'
        })
        
        return jsonify({'success': True, 'message': '测试脚本已开始执行'})
        
    except Exception as e:
        is_running = False
        return jsonify({'error': f'启动测试脚本失败: {str(e)}'}), 500

@app.route('/api/run', methods=['POST'])
def run_script():
    """运行脚本"""
    global script_process, is_running
    
    try:
        if is_running:
            return jsonify({'error': '脚本正在运行中'}), 400
        
        if not os.path.exists(SCRIPT_FILE):
            return jsonify({'error': f'脚本文件 {SCRIPT_FILE} 不存在'}), 404
        
        # 检查账号文件
        if not os.path.exists(ACCOUNTS_FILE):
            return jsonify({'error': f'账号文件 {ACCOUNTS_FILE} 不存在，请先添加账号'}), 404
        
        accounts = load_json_file(ACCOUNTS_FILE, [])
        if not accounts:
            return jsonify({'error': '没有可用的账号，请先添加账号'}), 400
        
        # 设置环境变量
        env = os.environ.copy()
        
        # 设置编码相关环境变量
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        if os.name == 'nt':  # Windows
            env['CHCP'] = '65001'  # UTF-8编码页
        
        config = load_json_file(CONFIG_FILE, {})
        
        # 将配置转换为环境变量
        for key, value in config.items():
            if value is not None:
                if isinstance(value, bool):
                    env[key] = 'true' if value else 'false'
                elif isinstance(value, (int, float)):
                    env[key] = str(value)
                else:
                    env[key] = str(value)
        
        # 启动脚本
        script_process = subprocess.Popen(
            ['python', '-u', SCRIPT_FILE],  # -u 参数确保输出不被缓冲
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并stderr到stdout
            env=env,
            cwd=os.getcwd(),
            bufsize=0,  # 无缓冲
            universal_newlines=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        is_running = True
        
        # 启动日志监控
        log_handler = LogHandler(script_process, socketio)
        log_handler.start_monitoring()
        
        # 启动进程监控线程
        threading.Thread(target=monitor_process, args=(script_process, log_handler), daemon=True).start()
        
        socketio.emit('status', {
            'type': 'status',
            'status': '运行中'
        })
        
        return jsonify({'success': True, 'message': '脚本已开始执行'})
        
    except Exception as e:
        is_running = False
        return jsonify({'error': f'启动脚本失败: {str(e)}'}), 500

@app.route('/api/stop', methods=['POST'])
def stop_script():
    """停止脚本"""
    global script_process, is_running
    
    try:
        # 检查脚本是否真的在运行
        if script_process is None:
            is_running = False
            return jsonify({'error': '脚本未在运行'}), 400
        
        # 检查进程是否还存活
        if script_process.poll() is not None:
            # 进程已经结束，更新状态
            is_running = False
            script_process = None
            socketio.emit('status', {
                'type': 'status',
                'status': '已停止'
            })
            return jsonify({'success': True, 'message': '脚本已经停止'})
        
        # 进程还在运行，尝试停止
        if not is_running:
            # 状态不一致，但进程还在，强制停止
            print("检测到状态不一致，强制停止进程")
        
        # 尝试优雅关闭
        try:
            script_process.terminate()
            script_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 强制关闭
            script_process.kill()
            script_process.wait()
        
        is_running = False
        script_process = None
        
        socketio.emit('status', {
            'type': 'status',
            'status': '已停止'
        })
        
        socketio.emit('log', {
            'type': 'log',
            'message': '✅ 脚本已手动停止',
            'timestamp': time.time()
        })
        
        return jsonify({'success': True, 'message': '脚本已停止'})
        
    except Exception as e:
        # 即使出错也要确保状态重置
        is_running = False
        if script_process:
            try:
                script_process.kill()
            except:
                pass
            script_process = None
        
        socketio.emit('status', {
            'type': 'status',
            'status': '已停止'
        })
        
        return jsonify({'error': f'停止脚本失败: {str(e)}'}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取脚本状态"""
    global is_running, script_process
    
    # 同步状态检查
    if script_process is not None:
        if script_process.poll() is not None:
            # 进程已结束，更新状态
            is_running = False
            script_process = None
    
    # 确定状态
    if script_process is None:
        status = '待运行'
        is_running = False
    elif script_process.poll() is None:
        status = '运行中'
        is_running = True
    else:
        status = '已完成'
        is_running = False
        script_process = None
    
    return jsonify({
        'status': status,
        'is_running': is_running,
        'pid': script_process.pid if script_process else None
    })

def monitor_process(process, log_handler):
    """监控进程状态"""
    global is_running, script_process
    
    try:
        # 等待进程结束
        return_code = process.wait()
        
        # 先停止日志监控，这会读取剩余的缓冲区内容
        log_handler.stop()
        
        # 等待一段时间确保所有输出都被处理
        time.sleep(1.0)
        
        # 额外的读取尝试 - 确保所有输出都被获取
        try:
            # 尝试再次从stdout读取任何剩余内容
            remaining_lines = []
            if process.stdout:
                try:
                    # 尝试设置非阻塞模式（仅在非Windows系统）
                    if sys.platform != 'win32':
                        import fcntl
                        flags = fcntl.fcntl(process.stdout.fileno(), fcntl.F_GETFL)
                        fcntl.fcntl(process.stdout.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
                except:
                    pass
                
                # 尝试读取剩余行（限制次数避免无限循环）
                max_attempts = 50
                attempts = 0
                while attempts < max_attempts:
                    try:
                        line = process.stdout.readline()
                        if not line:
                            break
                        
                        # 尝试解码
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
                            try:
                                decoded_line = line.decode(encoding).strip()
                                if decoded_line:
                                    remaining_lines.append(decoded_line)
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            decoded_line = line.decode('utf-8', errors='replace').strip()
                            if decoded_line:
                                remaining_lines.append(decoded_line)
                                
                        attempts += 1
                    except (BlockingIOError, IOError):
                        # 没有更多数据可读
                        break
                    except Exception:
                        break
                
                # 发送所有剩余的行
                for line in remaining_lines:
                    print(f"[LOG] {line}")
                    socketio.emit('log', {
                        'type': 'log', 
                        'message': line,
                        'timestamp': time.time()
                    })
                    time.sleep(0.02)
                    
                print(f"[DEBUG] 读取到 {len(remaining_lines)} 行剩余输出")
                    
        except Exception as e:
            print(f"最终读取剩余输出时出错: {e}")
            # 如果上面的方法失败，尝试简单的communicate（可能已经没有内容了）
            try:
                stdout, _ = process.communicate(timeout=1)
                if stdout:
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
                        try:
                            text = stdout.decode(encoding)
                            lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
                            for line in lines:
                                print(f"[LOG] {line}")
                                socketio.emit('log', {
                                    'type': 'log',
                                    'message': line,
                                    'timestamp': time.time()
                                })
                            print(f"[DEBUG] 通过communicate读取到 {len(lines)} 行")
                            break
                        except UnicodeDecodeError:
                            continue
            except:
                pass
        
        # 再次等待确保所有日志都已发送
        time.sleep(0.5)
        
        # 发送完成状态
        if return_code == 0:
            socketio.emit('status', {
                'type': 'status',
                'status': '已完成'
            })
            socketio.emit('log', {
                'type': 'log',
                'message': f'✅ 脚本执行完成，退出码: {return_code}',
                'timestamp': time.time()
            })
        else:
            socketio.emit('status', {
                'type': 'status',
                'status': '执行失败'
            })
            socketio.emit('log', {
                'type': 'log',
                'message': f'❌ 脚本执行失败，退出码: {return_code}',
                'timestamp': time.time()
            })
        
        is_running = False
        script_process = None
        
    except Exception as e:
        socketio.emit('log', {
            'type': 'log',
            'message': f'❌ 进程监控异常: {str(e)}',
            'timestamp': time.time()
        })
        is_running = False
        script_process = None

@socketio.on('connect')
def handle_connect():
    """WebSocket连接事件"""
    print('客户端已连接')
    emit('status', {
        'type': 'status',
        'status': '运行中' if is_running else '待运行'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket断开连接事件"""
    print('客户端已断开连接')

def signal_handler(sig, frame):
    """信号处理器"""
    global script_process, is_running
    
    print('\n收到停止信号，正在关闭...')
    
    if script_process and is_running:
        try:
            script_process.terminate()
            script_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            script_process.kill()
            script_process.wait()
    
    os._exit(0)

if __name__ == '__main__':
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("🚀 快手极速版Web管理界面")
    print("=" * 60)
    print(f"📁 工作目录: {os.getcwd()}")
    print(f"📄 脚本文件: {SCRIPT_FILE}")
    print(f"👥 账号文件: {ACCOUNTS_FILE}")
    print(f"⚙️  配置文件: {CONFIG_FILE}")
    print("=" * 60)
    print("🌐 Web界面地址: http://localhost:5000")
    print("📡 WebSocket地址: ws://localhost:5000/ws")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")
    print()
    
    try:
        # 启动Flask-SocketIO服务器
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
    except Exception as e:
        print(f"服务启动失败: {e}")
