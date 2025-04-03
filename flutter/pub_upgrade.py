#!/usr/bin/env python3
import os
import re
import subprocess
import sys

import requests

# 从环境变量获取 API_KEY、API_URL 和 PRIVATE_URL_PREFIX
API_KEY = os.getenv("cloudsmithApiKey")
API_URL = os.getenv("cloudsmithApiUrl")
PRIVATE_URL_PREFIX = os.getenv("cloudsmithPrivateUrl")

# 检查必需的环境变量是否存在
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
    """获取私有仓库的最新包版本"""
    headers = {"X-Api-Key": API_KEY, "accept": "application/json"}
    response = requests.get(API_URL, headers=headers)
    response.raise_for_status()
    packages = response.json()
    latest_versions = {}

    for pkg in packages:
        name, version = pkg["name"], pkg["version"]
        if "+" in version:
            continue  # 过滤带 "+" 的版本

        if name not in latest_versions or compare_versions(version, latest_versions[name]) == 1:
            latest_versions[name] = version  # 只保留最新版本

    return latest_versions


def compare_versions(v1, v2):
    """语义化版本比较"""
    parts1, parts2 = [list(map(int, v.split('.'))) for v in (v1, v2)]
    while len(parts1) < len(parts2): parts1.append(0)
    while len(parts2) < len(parts1): parts2.append(0)

    return (parts1 > parts2) - (parts1 < parts2)


def process_dependency_block(dep_block, latest_versions, updated_deps):
    """解析并更新一个私有依赖块"""
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
            print(f"🔄 升级 {dep_name}: {current_version} -> {new_version}")
            dep_block[version_line_idx] = f"{match.group(1)}{new_version}\n"
            updated = True
            updated_deps.append(f"{dep_name}: {current_version} -> {new_version}")

    return dep_block, updated


def update_pubspec(pubspec_file, latest_versions):
    """更新 pubspec.yaml 文件中的私有库版本"""
    with open(pubspec_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    in_dependencies = False
    dep_block = []
    any_update = False
    updated_deps = []

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
                updated_block, updated = process_dependency_block(dep_block, latest_versions,
                                                                  updated_deps)
                new_lines.extend(updated_block)
                dep_block = []
                if updated:
                    any_update = True
            new_lines.append(line)
            continue

        if in_dependencies and not re.match(r'^ {2}', line):
            if dep_block:
                updated_block, updated = process_dependency_block(dep_block, latest_versions,
                                                                  updated_deps)
                new_lines.extend(updated_block)
                dep_block = []
                if updated:
                    any_update = True
            in_dependencies = False
            new_lines.append(line)
            continue

        if re.match(r'^ {2}\S+:', line):
            if dep_block:
                updated_block, updated = process_dependency_block(dep_block, latest_versions,
                                                                  updated_deps)
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
        updated_block, updated = process_dependency_block(dep_block, latest_versions, updated_deps)
        new_lines.extend(updated_block)
        if updated:
            any_update = True

    with open(pubspec_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    if any_update:
        print("✅ pubspec.yaml 更新完毕！")
    else:
        print("✅ pubspec.yaml 没有更新。")

    return any_update, updated_deps


def flutter_pub_get():
    """执行 flutter pub get"""
    print("执行 flutter pub get...")
    result = subprocess.run(["flutter", "pub", "get"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"❌ flutter pub get 失败：{result.stderr.decode()}")
        sys.exit(1)
    print("✅ flutter pub get 执行成功！")


def git_commit_and_push(updated_deps):
    """提交更新并推送到远程仓库"""
    commit_message = "up deps:\n" + "\n".join(updated_deps) if updated_deps else "up deps"

    print("正在提交更新到 Git...")
    result = subprocess.run(["git", "add", "pubspec.yaml", "pubspec.lock"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"❌ git add 失败：{result.stderr.decode()}")
        sys.exit(1)

    result = subprocess.run(["git", "commit", "-m", commit_message], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"❌ git commit 失败：{result.stderr.decode()}")
        sys.exit(1)

    result = subprocess.run(["git", "push"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"❌ git push 失败：{result.stderr.decode()}")
        sys.exit(1)

    print("✅ 提交并推送成功！")


def main():
    pubspec_file = "pubspec.yaml"

    git_pull()

    try:
        latest_versions = get_latest_packages()
    except Exception as e:
        print("❌ 获取最新包信息失败：", e)
        return

    any_update, updated_deps = update_pubspec(pubspec_file, latest_versions)

    if any_update:
        flutter_pub_get()
        git_commit_and_push(updated_deps)
        print("✅ 版本内容：\n", updated_deps)
        print("✅ 版本更新完成！")
    else:
        print("❌ 没有更新任何依赖。")


if __name__ == "__main__":
    main()
