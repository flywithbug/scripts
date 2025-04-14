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
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

def clone_repo():
    if REPO_DIR.exists():
        shutil.rmtree(REPO_DIR)

    print("🔄 克隆工具仓库...")
    result = run(["git", "clone", REPO_URL, str(REPO_DIR)], stdout=PIPE, stderr=PIPE)
    if result.returncode != 0:
        print("❌ 仓库克隆失败：", result.stderr.decode())
        sys.exit(1)
    print("✅ 仓库克隆成功！")

    # 获取 commit hash
    os.chdir(REPO_DIR)
    result = run(["git", "rev-parse", "HEAD"], stdout=PIPE)
    commit_hash = result.stdout.decode().strip()
    VERSION_FILE.write_text(commit_hash)
    print(f"📦 当前版本: {commit_hash}")

    return REPO_DIR

def create_wrapper(script_path):
    cmd_name = script_path.stem
    wrapper = BIN_DIR / cmd_name

    if PLATFORM == "win32":
        wrapper = wrapper.with_suffix('.bat')
        content = f'@python "{script_path}" %*\n'
    else:
        content = f"""#!/bin/sh
exec python3 "{script_path}" "$@"
"""
    with open(wrapper, 'w') as f:
        f.write(content)

    if PLATFORM != "win32":
        wrapper.chmod(0o755)

    print(f"    🔗 已连接: {wrapper} -> {script_path}")

def install_commands(repo_path):
    tool_dirs = [repo_path / "flutter", repo_path / "tools"]

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
    path_str = os.getenv('PATH', '')
    if str(BIN_DIR) not in path_str.split(os.pathsep):
        print("\n⚠️  请将以下目录加入 PATH 环境变量:")
        print(f"  {BIN_DIR}")
        if PLATFORM == "win32":
            print(f"\n👉 执行命令: setx PATH \"%PATH%;{BIN_DIR}\"")
        else:
            print(f"\n👉 添加以下内容到 ~/.bashrc 或 ~/.zshrc:")
            print(f'export PATH="$PATH:{BIN_DIR}')

def main():
    setup_environment()

    repo_path = clone_repo()
    print("🔧 安装脚本工具中...")
    install_commands(repo_path)

    print("\n📌 当前可用命令:")
    for cmd in BIN_DIR.glob("*"):
        if not cmd.name.startswith('.'):
            print(f"  {cmd.name}")

    check_path()

if __name__ == '__main__':
    main()
