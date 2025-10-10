#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志输出脚本
"""

import time
import sys
import os

# 强制设置UTF-8编码
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def main():
    print("🚀 测试脚本开始执行...")
    sys.stdout.flush()
    time.sleep(1)
    
    print("✅ 这是一条成功日志")
    sys.stdout.flush()
    time.sleep(1)
    
    print("⚠️ 这是一条警告日志") 
    sys.stdout.flush()
    time.sleep(1)
    
    print("❌ 这是一条错误日志")
    sys.stdout.flush()
    time.sleep(1)
    
    print("📊 正在执行任务1...")
    sys.stdout.flush()
    time.sleep(2)
    
    print("💰 账号[测试账号] 获得100金币")
    sys.stdout.flush()
    time.sleep(1)
    
    print("🎯 账号[测试账号] 执行看广告得金币任务...")
    sys.stdout.flush()
    time.sleep(2)
    
    print("✅ 账号[测试账号] 看广告得金币任务完成")
    sys.stdout.flush()
    time.sleep(1)
    
    for i in range(5):
        print(f"📝 执行步骤 {i+1}/5...")
        sys.stdout.flush()
        time.sleep(1)
    
    print("🎉 测试脚本执行完成！")
    sys.stdout.flush()
    
if __name__ == "__main__":
    main()
