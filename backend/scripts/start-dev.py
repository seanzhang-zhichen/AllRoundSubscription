#!/usr/bin/env python3
"""
开发环境启动脚本
"""
import subprocess
import sys
import os
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

def run_command(command, cwd=None):
    """运行命令"""
    print(f"执行命令: {command}")
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd or PROJECT_ROOT,
        capture_output=False
    )
    return result.returncode == 0

def main():
    """主函数"""
    print("🚀 启动开发环境...")
    
    # 检查.env文件
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print("⚠️  .env文件不存在，从.env.example复制...")
        env_example = PROJECT_ROOT / ".env.example"
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ .env文件创建成功")
        else:
            print("❌ .env.example文件不存在")
            return False
    
    # 启动服务
    print("🔄 启动FastAPI服务...")
    success = run_command("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    
    if success:
        print("✅ 开发环境启动成功")
        print("📝 API文档: http://localhost:8000/docs")
        print("🔍 健康检查: http://localhost:8000/health")
    else:
        print("❌ 开发环境启动失败")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)