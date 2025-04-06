#!/usr/bin/env python3
import os
import sys
import stat
import shutil
import zipfile
import tempfile
from pathlib import Path
from urllib.request import urlretrieve

# 配置参数
ZIP_URL = "https://github.com/flywithbug/scripts/archive/refs/heads/master.zip"  # 替换为实际zip地址
INSTALL_DIR = Path.home() / ".script_tool"
BIN_DIR = Path.home() / ".local/bin"
PLATFORM = sys.platform

def setup_environment():
    """创建必要目录并设置权限"""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)

def download_and_extract_zip():
    """下载 zip 文件并解压到 repo 目录"""
    print("下载脚本包...")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "scripts.zip"
        urlretrieve(ZIP_URL, zip_path)

        print("解压脚本包...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        # 假设zip解压后是 scripts-main/
        extracted_folder = Path(tmpdir) / "scripts-main"
        repo_dir = INSTALL_DIR / "repo"

        # 清理旧版本
        if repo_dir.exists():
            shutil.rmtree(repo_dir)

        shutil.move(str(extracted_folder), repo_dir)
        print("脚本包已安装到本地！")
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
        repo_path / "flutter",
        repo_path / "tools"
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
    repo_path = download_and_extract_zip()
    print("开始安装脚本工具...")
    install_commands(repo_path)

    print("\n✅ 安装完成！可用命令列表:")
    for cmd in BIN_DIR.glob("*"):
        if not cmd.name.startswith('.'):
            print(f"  {cmd.name}")

    check_path()
