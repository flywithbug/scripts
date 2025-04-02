#!/usr/bin/env python3
import os
import sys
import stat
import subprocess

# 设置当前脚本为可执行（相当于 chmod +x 自身）
def set_self_executable():
    script_path = os.path.abspath(__file__)
    mode = os.stat(script_path).st_mode
    if not (mode & stat.S_IXUSR):
        print("设置当前脚本为可执行...")
        os.chmod(script_path, mode | stat.S_IXUSR)

# 仓库地址及本地路径（当前目录下隐藏目录 .scripts）
REPO_URL = "https://github.com/flywithbug/scripts.git"
REPO_DIR = os.path.join(os.getcwd(), ".scripts")
# 目标安装目录，需要该目录在 PATH 中（默认安装到 /usr/local/bin）
TARGET_DIR = "/usr/local/bin"

def run_command(command, cwd=None):
    """
    执行命令，遇到错误则退出程序。
    """
    try:
        subprocess.run(command, check=True, cwd=cwd)
    except subprocess.CalledProcessError:
        print("执行命令失败: " + " ".join(command))
        sys.exit(1)

def clone_or_update_repo():
    """
    如果本地仓库不存在则克隆，否则执行 git pull 更新仓库。
    """
    if not os.path.exists(REPO_DIR):
        print(f"克隆仓库 {REPO_URL} 到 {REPO_DIR} ...")
        run_command(["git", "clone", REPO_URL, REPO_DIR])
    else:
        print(f"更新仓库 {REPO_DIR} ...")
        run_command(["git", "pull"], cwd=REPO_DIR)
    print("仓库更新完成。")

def is_script(file_path):
    """
    判断文件是否为脚本：
      - 如果首行以 "#!" 开头，则认为是脚本；
      - 或者文件扩展名为 .sh 或 .py
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line.startswith("#!"):
                return True
    except Exception:
        return False

    if file_path.endswith(".sh") or file_path.endswith(".py"):
        return True

    return False

def install_scripts():
    """
    遍历仓库中所有文件，将判断为脚本的文件在 TARGET_DIR 下创建符号链接，
    链接名称为脚本文件的 basename（如需去掉扩展名，可修改此处）。
    """
    for root, dirs, files in os.walk(REPO_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            if is_script(file_path):
                command_name = file  # 如有需要可去掉扩展名： os.path.splitext(file)[0]
                target_path = os.path.join(TARGET_DIR, command_name)
                print(f"将文件 {file_path} 安装为命令 {command_name} ...")
                # 如果目标已存在，则先删除（使用 sudo 删除）
                if os.path.exists(target_path) or os.path.islink(target_path):
                    print(f"删除已存在的 {target_path} ...")
                    run_command(["sudo", "rm", "-f", target_path])
                # 创建符号链接（使用 sudo 创建）
                run_command(["sudo", "ln", "-s", file_path, target_path])
    print("所有脚本安装完毕。")

def main():
    set_self_executable()  # 设置当前脚本为可执行
    clone_or_update_repo()
    install_scripts()

if __name__ == "__main__":
    main()
