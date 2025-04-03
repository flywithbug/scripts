#!/usr/bin/env python3
import os
import re

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


def get_latest_packages():
    """
    获取私有仓库的最新包版本，返回字典 {包名: 最新版本}
    处理多个版本的情况，确保只保留最新的版本。
    """
    headers = {"X-Api-Key": API_KEY, "accept": "application/json"}
    response = requests.get(API_URL, headers=headers)
    response.raise_for_status()
    packages = response.json()

    latest_versions = {}

    for pkg in packages:
        name, version = pkg["name"], pkg["version"]
        if name not in latest_versions or compare_versions(version, latest_versions[name]) == 1:
            latest_versions[name] = version  # 只保留最高版本

    return latest_versions


def compare_versions(v1, v2):
    """
    纯 Python 代码实现语义化版本比较：
    - 返回 1：v1 > v2
    - 返回 0：v1 == v2
    - 返回 -1：v1 < v2
    """
    parts1, parts2 = [list(map(int, v.split('.'))) for v in (v1, v2)]
    while len(parts1) < len(parts2): parts1.append(0)
    while len(parts2) < len(parts1): parts2.append(0)

    return (parts1 > parts2) - (parts1 < parts2)


def process_dependency_block(dep_block, latest_versions):
    """
    解析并更新一个私有依赖块（仅限 Cloudsmith 私有库）。
    **完全保留格式和注释**
    """
    dep_name = None
    version_line_idx = -1
    updated = False  # 记录是否有更新

    # 识别包名、是否是私有库
    for idx, line in enumerate(dep_block):
        match = re.match(r'^( {2})(\S+):', line)
        if match:
            dep_name = match.group(2)

        if "hosted:" in line and PRIVATE_URL_PREFIX in "".join(dep_block):
            break
    else:
        return dep_block, updated  # 不是私有库

    if dep_name not in latest_versions:
        return dep_block, updated  # 私有库但无最新版本信息，跳过

    new_version = latest_versions[dep_name]

    # 找到 `version:` 行
    for idx, line in enumerate(dep_block):
        if re.match(r'^\s*version:\s*\S+', line):
            version_line_idx = idx
            break

    if version_line_idx == -1:
        return dep_block, updated  # 没有 `version:` 行，跳过

    # 检查并更新版本
    match = re.match(r'(\s*version:\s*)(\S+)', dep_block[version_line_idx])
    if match:
        current_version = match.group(2)
        if compare_versions(current_version, new_version) == -1:
            print(f"🔄 升级 {dep_name}: {current_version} -> {new_version}")
            dep_block[version_line_idx] = f"{match.group(1)}{new_version}\n"
            updated = True  # 标记为已更新

    return dep_block, updated


def update_pubspec(pubspec_file, latest_versions):
    """
    读取 pubspec.yaml 并**仅**更新私有库版本（保留排版和注释）。
    """
    with open(pubspec_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    in_dependencies = False
    dep_block = []
    any_update = False  # 记录是否有更新

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
                    any_update = True  # 如果有更新，标记
            new_lines.append(line)
            continue

        if in_dependencies and not re.match(r'^ {2}', line):
            if dep_block:
                updated_block, updated = process_dependency_block(dep_block, latest_versions)
                new_lines.extend(updated_block)
                dep_block = []
                if updated:
                    any_update = True  # 如果有更新，标记
            in_dependencies = False
            new_lines.append(line)
            continue

        if re.match(r'^ {2}\S+:', line):
            if dep_block:
                updated_block, updated = process_dependency_block(dep_block, latest_versions)
                new_lines.extend(updated_block)
                dep_block = []
                if updated:
                    any_update = True  # 如果有更新，标记
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
            any_update = True  # 如果有更新，标记

    with open(pubspec_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    if any_update:
        print("✅ pubspec.yaml 更新完毕！")
    else:
        print("✅ pubspec.yaml 没有更新。")


def main():
    pubspec_file = "pubspec.yaml"
    try:
        latest_versions = get_latest_packages()
    except Exception as e:
        print("❌ 获取最新包信息失败：", e)
        return
    update_pubspec(pubspec_file, latest_versions)


if __name__ == "__main__":
    main()
