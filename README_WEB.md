# 快手极速版Web管理界面

## 🌟 功能特性

- 📱 **账号管理**: 添加、编辑、删除账号信息，支持JSON导入导出
- ⚙️ **配置管理**: 可视化配置脚本参数（卡密、提现时间、金币阈值等）
- 🚀 **脚本执行**: 一键启动脚本，实时显示运行状态
- 📊 **实时日志**: WebSocket实时显示脚本执行日志，支持日志分类显示
- 🎯 **状态监控**: 显示账号数量、脚本状态、运行时间等信息

## 🚀 快速启动

### Windows 用户
双击运行 `start_web.bat` 文件

### Linux/Mac 用户
```bash
./start_web.sh
```

### 手动启动
```bash
# 安装依赖
pip install -r requirements.txt

# 启动Web服务
python start_web.py
```

## 🌐 访问界面

启动成功后，在浏览器中访问: [http://localhost:5000](http://localhost:5000)

界面将自动在默认浏览器中打开。

## 📁 文件说明

### 核心文件
- `index.html` - Web前端界面（Vue.js + Element Plus）
- `app.py` - 后端服务（Flask + SocketIO）
- `start_web.py` - Python启动脚本
- `Kuaishou.py` - 原快手极速版脚本

### 启动脚本
- `start_web.bat` - Windows批处理启动脚本
- `start_web.sh` - Linux/Mac Shell启动脚本

### 配置文件
- `accounts.json` - 账号数据文件
- `config.json` - 脚本配置文件
- `requirements.txt` - Python依赖包列表

## 📱 界面功能详解

### 1. 状态面板
- **账号总数**: 显示当前配置的账号数量
- **脚本状态**: 显示脚本运行状态（待运行/运行中/已完成/已停止）
- **运行时间**: 显示脚本运行时长
- **开始执行**: 一键启动脚本执行

### 2. 账号管理
- **添加账号**: 手动添加单个账号（Salt、Cookie、代理）
- **编辑账号**: 修改现有账号信息
- **删除账号**: 删除不需要的账号
- **导入JSON**: 批量导入账号数据
- **导出JSON**: 导出账号数据到文件

#### 账号格式说明
```json
[
  {
    "salt": "your_salt_here",
    "cookie": "your_cookie_here",
    "proxy": "127.0.0.1:1080"  // 可选
  }
]
```

### 3. 配置管理
- **卡密(LX_KM)**: 脚本所需的卡密
- **优化模式(LX_YH)**: 是否启用优化模式
- **开发模式**: 是否启用调试模式
- **任务黑名单**: 需要跳过的任务（如: sign,box,look）
- **并发数量**: 同时执行的账号数量
- **提现时间**: 自动提现的时间点（0-23小时）
- **提现金额**: 提现金额（元）
- **金币阈值**: 达到此金币数时停止任务

### 4. 实时日志
- **实时显示**: 通过WebSocket实时显示脚本执行日志
- **日志分类**: 不同类型的日志有不同颜色显示
  - 🔴 错误日志（红色）
  - 🟡 警告日志（黄色）
  - 🟢 成功日志（绿色）
  - 🔵 信息日志（蓝色）
- **自动滚动**: 日志自动滚动到最新内容
- **清空日志**: 一键清空当前显示的日志
- **停止脚本**: 强制停止正在运行的脚本

## ⚙️ 配置说明

### 账号配置格式

#### JSON格式（推荐）
```json
[
  {
    "salt": "salt1",
    "cookie": "complete_cookie_string_here",
    "proxy": "127.0.0.1:1080"
  },
  {
    "salt": "salt2", 
    "cookie": "complete_cookie_string_here"
  }
]
```

#### 文本格式
```
salt1#cookie1#proxy1
salt2#cookie2
salt3#cookie3#proxy3
```

### 脚本配置说明

| 配置项 | 说明 | 示例 |
|--------|------|------|
| LX_KM | 脚本卡密 | "your_card_key" |
| LX_YH | 优化模式开关 | true/false |
| DEV_MODE | 开发调试模式 | true/false |
| LX_TASK_BLACKLIST | 任务黑名单 | "sign,box" |
| MAX_CONCURRENCY | 最大并发数 | 5 |
| WITHDRAW_HOUR | 提现时间(小时) | 12 |
| WITHDRAW_AMOUNT | 提现金额(元) | 0.3 |
| COIN_THRESHOLD | 金币阈值 | 1000 |

## 🔧 技术架构

### 前端技术栈
- **Vue.js 3**: 渐进式JavaScript框架
- **Element Plus**: Vue 3组件库
- **Axios**: HTTP客户端
- **WebSocket**: 实时通信

### 后端技术栈
- **Flask**: Python Web框架
- **Flask-SocketIO**: WebSocket支持
- **Flask-CORS**: 跨域资源共享
- **subprocess**: 进程管理

## 🛠️ 故障排除

### 1. 端口被占用
```
[Errno 10048] 通常每个套接字地址只允许使用一次
```
**解决方案**: 关闭占用5000端口的程序，或修改`app.py`中的端口号

### 2. 依赖包缺失
```
ModuleNotFoundError: No module named 'flask'
```
**解决方案**: 运行 `pip install -r requirements.txt`

### 3. 脚本文件不存在
```
脚本文件 Kuaishou.py 不存在
```
**解决方案**: 确保`Kuaishou.py`文件在同一目录下

### 4. 账号文件格式错误
```
账号数据必须是数组格式
```
**解决方案**: 检查`accounts.json`文件格式是否正确

## 📝 注意事项

1. **端口占用**: 默认使用5000端口，请确保端口未被占用
2. **文件权限**: 确保有读写`accounts.json`和`config.json`的权限
3. **Python版本**: 建议使用Python 3.7+
4. **网络环境**: 需要稳定的网络连接
5. **浏览器兼容**: 建议使用Chrome、Firefox、Edge等现代浏览器

## 🆘 获取帮助

如果遇到问题，请检查:
1. 是否正确安装了所有依赖包
2. Python版本是否兼容
3. 文件是否完整存在
4. 网络连接是否正常
5. 控制台是否有错误信息

## 🔄 更新日志

### v1.0.0
- ✨ 初始版本发布
- 📱 完整的账号管理功能
- ⚙️ 可视化配置管理
- 🚀 一键脚本执行
- 📊 实时日志显示
- 🌐 现代化Web界面

---

**快手极速版Web管理界面** - 让脚本管理更简单！ 🚀
