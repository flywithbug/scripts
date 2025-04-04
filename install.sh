#!/bin/bash

set -e

echo "📦 正在下载并运行安装脚本..."

curl -fsSL https://raw.githubusercontent.com/flywithbug/scripts/master/tools/script_tools.py |
python3

echo "✅ 脚本库安装完成！"
