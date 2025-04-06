#!/usr/bin/env python3
import os
import sys
import stat
import shutil
import tempfile
import zipfile
import json
from pathlib import Path
from urllib.request import urlretrieve, urlopen
from subprocess import call

# 配置参数
REPO_OWNER = "flywithbug"
REPO_NAME = "scripts"
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/master.zip"
COMMIT_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/master"

INSTALL_DIR = Path.home() / ".script_tool"
REPO_DIR = INSTALL_DIR / "repo"
VERSION_FILE = INSTALL_DIR / ".version"
BIN_DIR = Path.home() / ".local/bin"
PLATFORM = sys.platform

def get_latest_commit_hash():
    """获取 GitHub 仓库 master 分支的最新 commit hash"""
    try:
        with urlopen(COMMIT_API_URL) as response:
            data = json.load(response)
            return data['sha']
    except Exception as e:
        print(f"❌ 获取最新 commit 失败: {e}")
        return None

def get_local_commit_hash():
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return None

def save_local_commit_hash(commit_hash):
    VERSION_FILE.write_text(commit_hash)

def setup_environment():
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

def download_and_extract_zip():
    """下载 zip 文件并更新 repo 目录的内容"""
    print("📦 正在下载脚本包...")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "scripts.zip"
        urlretrieve(ZIP_URL, zip_path)
        print(f"📥 下载完成: {zip_path}")

        print("📂 解压脚本包...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        extracted_folder = next(Path(tmpdir).glob("scripts-*"))
        print(f"📁 解压路径: {extracted_folder}")

        # 清空 repo_dir
        for item in REPO_DIR.iterdir() if REPO_DIR.exists() else []:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        # 复制新内容
        for item in extracted_folder.iterdir():
            dest = REPO_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        print(f"✅ 脚本包已更新到: {REPO_DIR}")
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
    tool_dirs = [
        repo_path / "flutter",
        repo_path / "tools"
    ]

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
            print(f'export PATH="$PATH:{BIN_DIR}"')

def main():
    setup_environment()

    latest_commit = get_latest_commit_hash()
    local_commit = get_local_commit_hash()

    if latest_commit and latest_commit == local_commit:
        print("✅ 已是最新版本，无需更新。")
    else:
        repo_path = download_and_extract_zip()
        print("🔧 安装脚本工具中...")
        install_commands(repo_path)
        if latest_commit:
            save_local_commit_hash(latest_commit)

    print("\n📌 当前可用命令:")
    for cmd in BIN_DIR.glob("*"):
        if not cmd.name.startswith('.'):
            print(f"  {cmd.name}")

    check_path()

if __name__ == '__main__':
    main()
