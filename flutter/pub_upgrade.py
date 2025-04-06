#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import threading
import time
from itertools import cycle

import requests

# 从环境变量获取 API_KEY、API_URL 和 PRIVATE_URL_PREFIX
API_KEY = os.getenv("cloudsmithApiKey")
API_URL = os.getenv("cloudsmithApiUrl")
PRIVATE_URL_PREFIX = os.getenv("cloudsmithPrivateUrl")

# 获取提交信息，默认为 "up deps"
commit_message = sys.argv[1] if len(sys.argv) > 1 else "up deps"
commit_updates = []  # 存储依赖更新日志

# 检查环境变量
if not API_KEY:
    print("❌ 环境变量 cloudsmithApiKey 未设置！")
    exit(1)
if not API_URL:
    print("❌ 环境变量 cloudsmithApiUrl 未设置！")
    exit(1)
if not PRIVATE_URL_PREFIX:
    print("❌ 环境变量 cloudsmithPrivateUrl 未设置！")
    exit(1)


def git_pull():
    """拉取最新的代码"""
    print("正在拉取最新代码...")
    result = subprocess.run(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"❌ 拉取代码失败：{result.stderr.decode()}")
        sys.exit(1)
    print("✅ 代码拉取完成。")


def get_latest_packages():
    """获取私有仓库最新包版本"""
    headers = {"X-Api-Key": API_KEY, "accept": "application/json"}
    response = requests.get(API_URL, headers=headers)
    response.raise_for_status()
    packages = response.json()
    latest_versions = {}

    for pkg in packages:
        name, version = pkg["name"], pkg["version"]
        if "+" in version:
            continue  # 跳过包含 "+" 的版本
        if name not in latest_versions or compare_versions(version, latest_versions[name]) == 1:
            latest_versions[name] = version  # 只保留最高版本

    return latest_versions


def compare_versions(v1, v2):
    """语义化版本比较"""
    parts1, parts2 = [list(map(int, v.replace('^', '').split('.'))) for v in (v1, v2)]
    while len(parts1) < len(parts2): parts1.append(0)
    while len(parts2) < len(parts1): parts2.append(0)
    return (parts1 > parts2) - (parts1 < parts2)


def process_dependency_block(dep_block, latest_versions):
    """解析并更新私有依赖（保留格式和注释）"""
    dep_name = None
    version_line_idx = -1
    updated = False

    for idx, line in enumerate(dep_block):
        match = re.match(r'^( {2})(\S+):', line)
        if match:
            dep_name = match.group(2)

        if "hosted:" in line and PRIVATE_URL_PREFIX in "".join(dep_block):
            break
    else:
        return dep_block, updated

    if dep_name not in latest_versions:
        return dep_block, updated

    new_version = latest_versions[dep_name]

    for idx, line in enumerate(dep_block):
        if re.match(r'^\s*version:\s*\S+', line):
            version_line_idx = idx
            break

    if version_line_idx == -1:
        return dep_block, updated

    match = re.match(r'(\s*version:\s*)(\S+)', dep_block[version_line_idx])
    if match:
        current_version = match.group(2)
        if compare_versions(current_version, new_version) == -1:
            if current_version.startswith('^'):
                new_version = f"^{new_version}"
            print(f"🔄 升级 {dep_name}: {current_version} -> {new_version}")
            commit_updates.append(
                f"🔄 {dep_name}: {current_version} → {new_version}")
            dep_block[version_line_idx] = f"{match.group(1)}{new_version}\n"
            updated = True

    return dep_block, updated


def update_pubspec(pubspec_file, latest_versions):
    """更新 pubspec.yaml 中的私有库"""
    with open(pubspec_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    in_dependencies = False
    dep_block = []
    any_update = False

    for line in lines:
        if re.match(r'^(dependencies|dependency_overrides):\s*$', line):
            in_dependencies = True
            new_lines.append(line)
            continue

        if not in_dependencies:
            new_lines.append(line)
            continue

        if line.strip() == "":
            if dep_block:
                updated_block, updated = process_dependency_block(dep_block, latest_versions)
                new_lines.extend(updated_block)
                dep_block = []
                if updated:
                    any_update = True
            new_lines.append(line)
            continue

        if in_dependencies and not re.match(r'^ {2}', line):
            if dep_block:
                updated_block, updated = process_dependency_block(dep_block, latest_versions)
                new_lines.extend(updated_block)
                dep_block = []
                if updated:
                    any_update = True
            in_dependencies = False
            new_lines.append(line)
            continue

        if re.match(r'^ {2}\S+:', line):
            if dep_block:
                updated_block, updated = process_dependency_block(dep_block, latest_versions)
                new_lines.extend(updated_block)
                dep_block = []
                if updated:
                    any_update = True
            dep_block.append(line)
        else:
            if dep_block:
                dep_block.append(line)
            else:
                new_lines.append(line)

    if dep_block:
        updated_block, updated = process_dependency_block(dep_block, latest_versions)
        new_lines.extend(updated_block)
        if updated:
            any_update = True

    with open(pubspec_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    return any_update


def loading_animation(stop_event):
    """加载动画"""
    spinner = cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
    while not stop_event.is_set():
        sys.stdout.write(f"\r{next(spinner)} 正在执行 flutter pub get... ")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r✅ flutter pub get 执行成功！    \n")
    sys.stdout.flush()


def flutter_pub_get():
    """执行 flutter pub get 并显示动画"""
    stop_event = threading.Event()
    loader_thread = threading.Thread(target=loading_animation, args=(stop_event,))
    loader_thread.start()

    process = subprocess.run(["flutter", "pub", "get"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    stop_event.set()
    loader_thread.join()

    if process.returncode != 0:
        print(f"\n❌ flutter pub get 失败：{process.stderr}")
        sys.exit(1)


def check_remote_branch():
    """检查当前分支是否有远程分支"""
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    current_branch = result.stdout.decode().strip()

    result = subprocess.run(["git", "ls-remote", "--heads", "origin", current_branch],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0 or not result.stdout:
        print("⚠️ 当前分支没有远程分支，仅提交到本地。")
        return False
    return True


def git_commit_and_push():
    """提交并推送 Git"""
    if commit_updates:
        full_commit_msg = "\n".join(commit_updates)
        subprocess.run(["git", "add", "pubspec.yaml", "pubspec.lock"])
        subprocess.run(["git", "commit", "-m", full_commit_msg])

        if check_remote_branch():
            subprocess.run(["git", "push"])
            print("✅ 提交并推送成功！")
        else:
            print("✅ 已提交到本地（未推送）。")


def main():
    git_pull()
    latest_versions = get_latest_packages()
    if update_pubspec("pubspec.yaml", latest_versions):
        flutter_pub_get()
        git_commit_and_push()
    else:
        print("❌ 没有更新任何依赖。")


if __name__ == "__main__":
    main()
