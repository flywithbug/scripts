#!/usr/bin/env python3
import os
import sys
import stat
import shutil
from pathlib import Path
from subprocess import call

# 配置参数
REPO_URL = "git@github.com:flywithbug/scripts.git"  # 替换为实际仓库地址
INSTALL_DIR = Path.home() / ".script_tool"
BIN_DIR = Path.home() / ".local/bin"  # 推荐使用标准bin目录
PLATFORM = sys.platform

def setup_environment():
    """创建必要目录并设置权限"""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

def clone_or_update_repo():
    """克隆或更新工具仓库"""
    repo_dir = INSTALL_DIR / "repo"

    if (repo_dir / ".git").exists():
        print("更新工具仓库...")
        os.chdir(repo_dir)
        if call(["git", "pull"]) != 0:
            print("仓库更新失败，请手动检查")
            sys.exit(1)
    else:
        print("克隆工具仓库...")
        if call(["git", "clone", REPO_URL, str(repo_dir)]) != 0:
            print("仓库克隆失败，请检查网络和仓库地址")
            sys.exit(1)
    return repo_dir

def create_wrapper(script_path):
    """创建跨平台执行包装器"""
    cmd_name = script_path.stem
    wrapper = BIN_DIR / cmd_name

    if PLATFORM == "win32":
        wrapper = wrapper.with_suffix('.bat')
        content = f'@python "{script_path}" %*\n'
    else:
        content = f"""#!/bin/sh
exec python3 "{script_path}" "$@"
"""

    # 写入包装器文件
    with open(wrapper, 'w') as f:
        f.write(content)

    # 设置可执行权限
    if PLATFORM != "win32":
        wrapper.chmod(0o755)

def install_commands(repo_path):
    """安装所有工具命令"""
    tool_dirs = [
        repo_path / "flutter",   # 示例工具目录
        repo_path / "tools"     # 其他工具目录
    ]

    for tool_dir in tool_dirs:
        if not tool_dir.exists():
            continue

        print(f"处理目录: {tool_dir.name}")
        for py_script in tool_dir.glob("*.py"):
            if py_script.name.startswith('_'):
                continue

            print(f"安装命令: {py_script.stem}")
            create_wrapper(py_script)

def check_path():
    """检查环境变量配置"""
    path_str = os.getenv('PATH', '')
    if str(BIN_DIR) not in path_str.split(os.pathsep):
        print("\n⚠️ 需要将以下目录加入PATH环境变量:")
        print(f"  {BIN_DIR}")

        if PLATFORM == "win32":
            print(f"\n执行命令: setx PATH \"%PATH%;{BIN_DIR}\"")
        else:
            print(f"\n添加以下内容到shell配置文件:")
            print(f'export PATH="$PATH:{BIN_DIR}"')

if __name__ == '__main__':
    setup_environment()
    repo_path = clone_or_update_repo()
    print("开始安装脚本工具...")
    install_commands(repo_path)

    print("\n✅ 安装完成！可用命令列表:")
    for cmd in BIN_DIR.glob("*"):
        if not cmd.name.startswith('.'):
            print(f"  {cmd.name}")

    check_path()