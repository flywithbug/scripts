#!/usr/bin/env python3
import re
import subprocess
from pathlib import Path


def parse_version_string(version_str):
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:\+([^\s]+))?$', version_str.strip())
    if not match:
        raise ValueError("版本号格式不正确，应为 x.y.z 或 x.y.z+build")
    major, minor, patch = map(int, match.group(1, 2, 3))
    build = match.group(4)
    return [major, minor, patch], build


def upgrade_version(version_parts, level):
    major, minor, patch = version_parts
    if level == 1:
        minor += 1
        patch = 0
    elif level == 2:
        patch += 1
    else:
        raise ValueError("升级级别只能为 1（minor）或 2（patch）")
    return [major, minor, patch]


def format_version(version_parts, build=None):
    version = f"{version_parts[0]}.{version_parts[1]}.{version_parts[2]}"
    return f"{version}+{build}" if build else version


def git_commit_and_push(new_version_str):
    """
    执行 git add + commit + push
    """
    try:
        subprocess.run(["git", "add", "pubspec.yaml"], check=True)
        subprocess.run(["git", "commit", "-m", f"chore: bump version to {new_version_str}"],
                       check=True)
        print(f"✅ Git commit 成功，提交信息: chore: bump version to {new_version_str}")
    except subprocess.CalledProcessError as e:
        print("❌ Git 提交失败:", e)
        return False

    try:
        subprocess.run(["git", "push"], check=True)
        print("✅ Git push 成功")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Git push 失败:", e)
        return False


def main():
    pubspec = Path("pubspec.yaml")
    if not pubspec.exists():
        print("❌ 找不到 pubspec.yaml 文件")
        return

    content = pubspec.read_text(encoding="utf-8")

    match = re.search(r'^version:\s*([0-9]+\.[0-9]+\.[0-9]+(?:\+[^\s]+)?)', content, re.MULTILINE)
    if not match:
        print("❌ pubspec.yaml 中未找到 version 字段")
        return

    old_version_str = match.group(1)
    version_parts, build = parse_version_string(old_version_str)

    print(f"📦 当前版本: {old_version_str}")
    print("请选择升级级别：")
    print("1 - 次版本号（minor）升级 → X.*Y*.0")
    print("2 - 补丁号（patch）升级 → X.Y.*Z*")

    level = input("请输入 1 或 2: ").strip()
    if level not in ("1", "2"):
        print("❌ 无效输入")
        return

    new_version_parts = upgrade_version(version_parts, int(level))
    new_version_str = format_version(new_version_parts, build)

    print(f"✅ 版本将从 {old_version_str} 升级为 {new_version_str}")

    new_content = re.sub(
        r'^(version:\s*)([0-9]+\.[0-9]+\.[0-9]+(?:\+[^\s]+)?)',
        rf'\g<1>{new_version_str}',
        content,
        flags=re.MULTILINE
    )

    pubspec.write_text(new_content, encoding="utf-8")
    print("✅ pubspec.yaml 已更新")

    # 提交并推送
    git_commit_and_push(new_version_str)


if __name__ == "__main__":
    main()
