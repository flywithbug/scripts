#!/usr/bin/env python3
import argparse
import re
import datetime
import os
import subprocess

def run_command(command):
    """执行命令行命令，遇到错误时报错"""
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"执行命令失败: {' '.join(command)}")
        exit(1)

def git_pull():
    """拉取最新代码"""
    print("拉取最新代码...")
    run_command(["git", "pull"])
    print("代码已更新。")

def increment_version(version):
    """版本号自增"""
    parts = version.strip().split('.')
    major, minor, patch = map(int, parts)

    if patch < 99:
        patch += 1
    else:
        patch = 0
        minor += 1

    return f"{major}.{minor}.{patch}"

def update_pubspec_preserve_format(pubspec_path):
    """更新 pubspec.yaml 版本号，保持原格式"""
    if not os.path.exists(pubspec_path):
        print(f"错误：找不到 {pubspec_path}")
        return None

    with open(pubspec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r"^(?P<prefix>\s*version\s*:\s*)(?P<quote>['\"]?)(?P<version>\d+\.\d+\.\d+)(?P=quote)"
    match = re.search(pattern, content, flags=re.MULTILINE)
    if not match:
        print("未在 pubspec.yaml 中找到 version 字段。")
        return None

    new_version = increment_version(match.group("version"))
    replacement = f"{match.group('prefix')}{match.group('quote')}{new_version}{match.group('quote')}"
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

    with open(pubspec_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"版本号已更新: {match.group('version')} -> {new_version}")
    return new_version

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

def git_commit(pubspec_path, changelog_path, new_version):
    """提交更新到 Git"""
    with open(pubspec_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r"^\s*name\s*:\s*['\"]?([\w\-\.]+)['\"]?", content, flags=re.MULTILINE)
    project_name = match.group(1) if match else "unknown"

    commit_message = f"build: {project_name} + {new_version}"

    run_command(["git", "add", pubspec_path, changelog_path])
    run_command(["git", "commit", "-m", commit_message])
    print(f"已提交 Git: {commit_message}")

    run_command(["git", "push"])
    print("Git 代码已推送。")

def flutter_pub_publish():
    """执行 Flutter 预检查 & 发布"""
    # print("执行 'flutter pub publish --dry-run'...")
    # run_command(["flutter", "pub", "publish", "--dry-run"])
    # print("预检查通过！")

    print("发布新版本...")
    run_command(["flutter", "pub", "publish", "--force"])
    print("Flutter 发布成功！")

def main():
    parser = argparse.ArgumentParser(description="自动更新版本，提交 Git 并发布 Flutter 包")
    parser.add_argument("--pubspec", default="pubspec.yaml", help="pubspec.yaml 文件路径")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="CHANGELOG.md 文件路径")
    parser.add_argument("--msg", nargs="+", default=["更新版本"], help="更新说明内容（不需要引号）")
    args = parser.parse_args()

    msg_text = " ".join(args.msg)  # 多词拼接

    git_pull()

    new_version = update_pubspec_preserve_format(args.pubspec)
    if new_version is None:
        return

    update_changelog(args.changelog, new_version, msg_text)
    git_commit(args.pubspec, args.changelog, new_version)

    flutter_pub_publish()

if __name__ == "__main__":
    main()

