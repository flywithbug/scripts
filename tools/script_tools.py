#!/usr/bin/env python3
import os
import sys
import stat
import shutil
import tempfile
import zipfile
import hashlib
from pathlib import Path
from urllib.request import urlretrieve
from subprocess import call

# 配置参数
ZIP_URL = "https://github.com/flywithbug/scripts/archive/refs/heads/master.zip"  # 替换为实际 ZIP 地址
INSTALL_DIR = Path.home() / ".script_tool"
BIN_DIR = Path.home() / ".local/bin"  # 推荐使用标准 bin 目录
PLATFORM = sys.platform
VERSION_FILE = INSTALL_DIR / "version.txt"  # 记录版本的文件

def setup_environment():
    """创建必要目录并设置权限"""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

def calculate_version_hash(url):
    """计算 URL 的哈希值，作为版本标识"""
    return hashlib.sha256(url.encode('utf-8')).hexdigest()

def get_last_version():
    """读取记录的上次版本"""
    if VERSION_FILE.exists():
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_current_version(version_hash):
    """保存当前版本的哈希值"""
    with open(VERSION_FILE, 'w') as f:
        f.write(version_hash)

def download_and_extract_zip():
    """下载 zip 文件并更新 repo 目录的内容"""
    print("下载脚本包...")

    # 计算当前版本的哈希值
    current_version = calculate_version_hash(ZIP_URL)
    last_version = get_last_version()

    # 如果版本没有变化，则跳过更新
    if current_version == last_version:
        print("版本未更改，跳过更新。")
        return INSTALL_DIR / "repo"

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "scripts.zip"
        urlretrieve(ZIP_URL, zip_path)

        print("解压脚本包...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        # 找到解压出来的目录（如 scripts-main）
        extracted_folder = next(Path(tmpdir).glob("scripts-*"))
        repo_dir = INSTALL_DIR / "repo"

        # 确保目标目录存在
        repo_dir.mkdir(parents=True, exist_ok=True)

        # 清空 repo_dir 中的旧内容
        for item in repo_dir.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        # 复制新内容到 repo_dir
        for item in extracted_folder.iterdir():
            dest = repo_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        print("脚本包已更新！")

        # 保存当前版本
        save_current_version(current_version)

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

    with open(wrapper, 'w') as f:
        f.write(content)

    if PLATFORM != "win32":
        wrapper.chmod(0o755)

def install_commands(repo_path):
    """安装所有工具命令"""
    tool_dirs = [
        repo_path / "flutter",   # 示例工具目录
        repo_path / "tools"      # 其他工具目录
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
    """检查 PATH 环境变量配置"""
    path_str = os.getenv('PATH', '')
    if str(BIN_DIR) not in path_str.split(os.pathsep):
        print("\n⚠️ 需要将以下目录加入 PATH 环境变量:")
        print(f"  {BIN_DIR}")

        if PLATFORM == "win32":
            print(f"\n执行命令: setx PATH \"%PATH%;{BIN_DIR}\"")
        else:
            print(f"\n添加以下内容到 shell 配置文件 (如 ~/.bashrc 或 ~/.zshrc):")
            print(f'export PATH="$PATH:{BIN_DIR}"')

if __name__ == '__main__':
    setup_environment()
    repo_path = download_and_extract_zip()  # 下载并更新 repo
    print("开始安装脚本工具...")
    install_commands(repo_path)

    print("\n✅ 安装完成！可用命令列表:")
    for cmd in BIN_DIR.glob("*"):
        if not cmd.name.startswith('.'):
            print(f"  {cmd.name}")

    check_path()
