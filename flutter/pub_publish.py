#!/usr/bin/env python3
import argparse
import re
import datetime
import os
import subprocess

def run_command(command):
    """执行命令行命令，遇到错误时报错"""
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"执行命令失败: {' '.join(command)}")
        print(f"错误信息: {e.stderr}")
        exit(1)

def get_current_branch():
    """获取当前 Git 分支名称"""
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def git_pull():
    """拉取最新代码"""
    print("拉取最新代码...")
    run_command(["git", "pull"])
    print("代码已更新。")

def compare_versions(current_version, target_version):
    """比较两个版本号，返回 -1（小于）、0（等于）、1（大于）"""
    current_parts = list(map(int, current_version.split('.')))
    target_parts = list(map(int, target_version.split('.')))

    for i in range(3):  # 比较 MAJOR, MINOR, PATCH
        if current_parts[i] < target_parts[i]:
            return -1
        elif current_parts[i] > target_parts[i]:
            return 1
    return 0

def update_version(current_version, branch_version=None):
    """根据分支和当前版本号更新版本号"""
    if branch_version:
        # 分支是 release-X.Y.Z 格式
        if compare_versions(current_version, branch_version) < 0:
            # 当前版本低于分支版本，直接使用分支版本
            return branch_version
        elif compare_versions(current_version, branch_version) == 0:
            # 当前版本等于分支版本，递增补丁号
            parts = current_version.split('.')
            major, minor, patch = map(int, parts)
            return f"{major}.{minor}.{patch + 1}"

    # 非 release 分支，递增补丁号
    parts = current_version.split('.')
    major, minor, patch = map(int, parts)
    return f"{major}.{minor}.{patch + 1}"

def extract_project_name(pubspec_path):
    """从 pubspec.yaml 提取项目名称"""
    with open(pubspec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r"^\s*name\s*:\s*['\"]?([\w\-\.]+)['\"]?", content, flags=re.MULTILINE)
    return match.group(1) if match else "unknown"

def update_pubspec_preserve_format(pubspec_path):
    """更新 pubspec.yaml 版本号，保持原格式"""
    if not os.path.exists(pubspec_path):
        print(f"错误：找不到 {pubspec_path}")
        return None, None

    with open(pubspec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r"^(?P<prefix>\s*version\s*:\s*)(?P<quote>['\"]?)(?P<version>\d+\.\d+\.\d+)(?P=quote)"
    match = re.search(pattern, content, flags=re.MULTILINE)
    if not match:
        print("未在 pubspec.yaml 中找到 version 字段。")
        return None, None

    current_version = match.group("version")
    # 检查当前分支是否为 release-X.Y.Z
    current_branch = get_current_branch()
    branch_version = None
    branch_match = re.match(r"^release-(\d+\.\d+\.\d+)$", current_branch)
    if branch_match:
        branch_version = branch_match.group(1)

    new_version = update_version(current_version, branch_version)
    replacement = f"{match.group('prefix')}{match.group('quote')}{new_version}{match.group('quote')}"
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

    with open(pubspec_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"版本号已更新: {current_version} -> {new_version}")
    return new_version, current_version

def update_changelog(changelog_path, new_version, msg):
    """更新 CHANGELOG.md"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"## {new_version}\n\n- {now}\n- {msg}\n\n"

    if not os.path.exists(changelog_path):
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(header)
    else:
        with open(changelog_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(header + content)

    print(f"CHANGELOG.md 已更新: 版本 {new_version}")

def git_commit(pubspec_path, changelog_path, project_name, new_version):
    """提交更新到 Git"""
    commit_message = f"build: {project_name} + {new_version}"

    run_command(["git", "add", pubspec_path, changelog_path, "pubspec.lock"])
    run_command(["git", "commit", "-m", commit_message])
    print(f"已提交 Git: {commit_message}")

    run_command(["git", "push"])
    print("Git 代码已推送。")

def flutter_pub_get():
    """执行 flutter pub get"""
    print("执行 flutter pub get...")
    run_command(["flutter", "pub", "get"])
    print("flutter pub get 执行成功！")

def flutter_pub_publish():
    """执行 Flutter 预检查 & 发布"""
    print("发布新版本...")
    run_command(["flutter", "pub", "publish", "--force"])
    print("Flutter 发布成功！")

def main():
    parser = argparse.ArgumentParser(description="自动更新版本，提交 Git 并发布 Flutter 包")
    parser.add_argument("--pubspec", default="pubspec.yaml", help="pubspec.yaml 文件路径")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="CHANGELOG.md 文件路径")
    parser.add_argument("--msg", nargs="+", required=True, help="更新说明内容（不需要引号）")
    args = parser.parse_args()

    msg_text = " ".join(args.msg)

    git_pull()

    # 获取包名
    project_name = extract_project_name(args.pubspec)

    # 更新 pubspec.yaml
    new_version, old_version = update_pubspec_preserve_format(args.pubspec)
    if new_version is None:
        return

    # 更新 CHANGELOG.md
    update_changelog(args.changelog, new_version, msg_text)

    # 运行 flutter pub get
    flutter_pub_get()

    # 提交 Git
    git_commit(args.pubspec, args.changelog, project_name, new_version)

    # 发布 Flutter 包
    flutter_pub_publish()

    # 最终输出信息
    print(f"✅ 版本升级成功：{project_name} {old_version} → {new_version}")

if __name__ == "__main__":
    main()