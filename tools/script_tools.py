#!/usr/bin/env python3
import os
import sys
import shutil
from pathlib import Path
from subprocess import run, PIPE

# 配置参数
REPO_OWNER = "flywithbug"
REPO_NAME = "scripts"
REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git"

INSTALL_DIR = Path.home() / ".script_tool"
REPO_DIR = INSTALL_DIR / "repo"
VERSION_FILE = INSTALL_DIR / ".version"
BIN_DIR = Path.home() / ".local/bin"
PLATFORM = sys.platform

def setup_environment():
    """创建安装目录和二进制目录"""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

def clone_repo():
    """克隆仓库到临时目录并返回路径"""
    temp_dir = INSTALL_DIR / "temp_repo"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    print("🔄 克隆工具仓库...")
    result = run(["git", "clone", REPO_URL, str(temp_dir)], stdout=PIPE, stderr=PIPE, text=True)
    if result.returncode != 0:
        print("❌ 仓库克隆失败：", result.stderr)
        sys.exit(1)
    print("✅ 仓库克隆成功！")
    return temp_dir

def clean_old_installation():
    """清理旧的安装文件和链接"""
    print("🧹 清理旧的安装文件...")
    # 删除旧的 repo 目录
    if REPO_DIR.exists():
        shutil.rmtree(REPO_DIR)

    # 删除旧的版本文件
    if VERSION_FILE.exists():
        VERSION_FILE.unlink()

    # 删除旧的 wrapper 脚本
    tool_dirs = ["flutter", "tools"]
    for cmd in BIN_DIR.glob("*"):
        # 检查是否是本工具生成的 wrapper
        cmd_name = cmd.stem if PLATFORM == "win32" else cmd.name
        if any(cmd_name in (p.stem for p in (REPO_DIR / d).glob("*.py") if not p.name.startswith('_')) for d in tool_dirs):
            cmd.unlink()
            print(f"    🗑️ 已删除旧链接: {cmd}")

def update_installation(temp_dir):
    """更新安装：移动仓库、记录版本、创建 wrapper"""
    # 移动临时仓库到正式目录
    print("📂 更新仓库目录...")
    temp_dir.rename(REPO_DIR)

    # 获取 commit hash
    os.chdir(REPO_DIR)
    result = run(["git", "rev-parse", "HEAD"], stdout=PIPE, text=True)
    commit_hash = result.stdout.strip()
    VERSION_FILE.write_text(commit_hash)
    print(f"📦 当前版本: {commit_hash}")

def create_wrapper(script_path):
    """为脚本创建 wrapper"""
    cmd_name = script_path.stem
    wrapper = BIN_DIR / cmd_name

    if PLATFORM == "win32":
        wrapper = wrapper.with_suffix('.bat')
        content = f'@python "{script_path}" %*\n'
    else:
        content = f"""#!/bin/sh
exec python3 "{script_path}" "$@"
"""
    wrapper.write_text(content)

    if PLATFORM != "win32":
        wrapper.chmod(0o755)

    print(f"    🔗 已连接: {wrapper} -> {script_path}")

def install_commands():
    """安装命令"""
    tool_dirs = [REPO_DIR / "flutter", REPO_DIR / "tools"]
    for tool_dir in tool_dirs:
        if not tool_dir.exists():
            continue
        print(f"🚀 安装目录: {tool_dir.name}")
        for py_script in tool_dir.glob("*.py"):
            if py_script.name.startswith('_'):
                continue
            print(f"  ➜ 命令: {py_script.stem}")
            create_wrapper(py_script)

def check_path():
    """检查 PATH 环境变量"""
    path_str = os.getenv('PATH', '')
    if str(BIN_DIR) not in path_str.split(os.pathsep):
        print("\n⚠️ 请将以下目录加入 PATH 环境变量:")
        print(f"  {BIN_DIR}")
        if PLATFORM == "win32":
            print(f"\n👉 执行命令: setx PATH \"%PATH%;{BIN_DIR}\"")
        else:
            print(f"\n👉 添加以下内容到 ~/.bashrc 或 ~/.zshrc:")
            print(f'export PATH="$PATH:{BIN_DIR}"')

def main():
    """主函数"""
    setup_environment()

    # 先克隆仓库
    temp_dir = clone_repo()

    # 清理旧安装
    clean_old_installation()

    # 更新安装
    update_installation(temp_dir)
    print("🔧 安装脚本工具中...")
    install_commands()

    # 列出可用命令
    print("\n📌 当前可用命令:")
    for cmd in sorted(BIN_DIR.glob("*")):
        if not cmd.name.startswith('.'):
            print(f"  {cmd.name}")

    # 检查 PATH
    check_path()

if __name__ == '__main__':
    main()