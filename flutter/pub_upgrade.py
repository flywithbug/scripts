#!/usr/bin/env python3
import re
import subprocess
import sys
import threading
import time
from itertools import cycle
import argparse
import json


def get_latest_ap_packages():
    result = subprocess.run(
        ["flutter", "pub", "outdated", "--json"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("❌ flutter pub outdated 失败")
        print(result.stderr)
        exit(1)

    data = json.loads(result.stdout)
    outdated = {}

    for pkg_info in data.get("packages", []):
        pkg_name = pkg_info.get("package")
        if not pkg_name.startswith("ap_"):
            continue

        current = pkg_info.get("current", {}).get("version")
        latest = pkg_info.get("latest", {}).get("version")

        if is_valid_version(current) and is_valid_version(latest):
            if compare_versions(latest, current) > 0:
                outdated[pkg_name] = latest

    return outdated


# 解析命令行参数
parser = argparse.ArgumentParser(
    description="🛠 自动检查并更新 pubspec.yaml 中的私有依赖版本，并执行 Git 提交。",
    epilog="示例：python3 update_deps.py \"更新依赖版本\" --no-commit"
)
parser.add_argument(
    "commit_message",
    nargs="?",
    default="up deps",
    help="Git 提交信息（默认为 'up deps'）"
)
parser.add_argument(
    "--no-commit",
    action="store_true",
    help="只更新依赖但不提交到 Git"
)
args = parser.parse_args()

commit_message = args.commit_message
no_commit = args.no_commit
commit_updates = []  # 存储依赖更新日志


def get_current_branch():
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.decode().strip()


def has_remote_branch(branch_name):
    result = subprocess.run(["git", "ls-remote", "--heads", "origin", branch_name],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return bool(result.stdout)


def git_pull(branch):
    if has_remote_branch(branch):
        print(f"⬇️ 正在拉取远程分支 {branch}...")
        result = subprocess.run(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"❌ 拉取失败：{result.stderr.decode()}")
            sys.exit(1)
        print("✅ 拉取成功。")
    else:
        print("⚠️ 当前分支没有远程分支，跳过拉取。")


def is_valid_version(version) -> bool:
    """
    判断版本号是否有效，只允许包含数字和点（.）
    :param version: 版本号（任意类型）
    :return: 如果版本号有效（为字符串，且只包含数字和点），返回 True；否则返回 False
    """
    if not isinstance(version, str):
        return False
    return bool(re.fullmatch(r"^[0-9.]+$", version.strip()))


def compare_versions(v1, v2):
    parts1, parts2 = [list(map(int, v.replace('^', '').split('.'))) for v in (v1, v2)]
    while len(parts1) < len(parts2):
        parts1.append(0)
    while len(parts2) < len(parts1):
        parts2.append(0)
    return (parts1 > parts2) - (parts1 < parts2)


def process_dependency_block(dep_block, latest_versions):
    dep_name = None
    version_line_idx = -1
    updated = False

    for line in dep_block:
        match = re.match(r'^\s{2}(\S+):', line)
        if match:
            dep_name = match.group(1)
            break

    if dep_name is None or dep_name not in latest_versions:
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
            commit_updates.append(f"🔄 {dep_name}: {current_version} → {new_version}")
            dep_block[version_line_idx] = f"{match.group(1)}{new_version}\n"
            updated = True

    return dep_block, updated


def update_pubspec(pubspec_file, latest_versions):
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
    spinner = cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
    while not stop_event.is_set():
        sys.stdout.write(f"\r{next(spinner)} 正在执行 flutter pub get... ")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r✅ flutter pub get 执行成功！    \n")
    sys.stdout.flush()


def flutter_pub_get():
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


def git_commit_and_push(branch):
    if commit_updates:
        full_commit_msg = commit_message + "\n\n" + "\n".join(commit_updates)
        subprocess.run(["git", "add", "pubspec.yaml", "pubspec.lock"], check=True)
        subprocess.run(["git", "commit", "-m", full_commit_msg], check=True)
        if has_remote_branch(branch):
            subprocess.run(["git", "push"], check=True)
            print("✅ 提交并推送成功！")
        else:
            print("✅ 已提交到本地（未推送）。")


def main():
    branch = get_current_branch()
    git_pull(branch)
    latest_versions = get_latest_ap_packages()
    if update_pubspec("pubspec.yaml", latest_versions):
        flutter_pub_get()
        if not no_commit:
            git_commit_and_push(branch)
        else:
            print("📦 已更新依赖，但未提交到 Git（--no-commit）。")
    else:
        print("❌ 没有更新任何依赖。")


if __name__ == "__main__":
    main()
