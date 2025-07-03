#!/bin/bash

# === 配置项 ===
ORG="apex-dao-llc"
REPO="app"
CUTOFF_DATE="2024-06-06T00:00:00Z"  # 删除早于此时间的包
DRY_RUN=false   # 改为 true 可仅打印不执行删除

echo "🧹 开始清理 Cloudsmith 仓库: $ORG/$REPO"
echo "📅 删除上传时间早于 $CUTOFF_DATE 的包..."
echo "🧪 Dry-Run 模式: $DRY_RUN"

PAGE=130
HAS_MORE=true

while $HAS_MORE; do
  echo "📄 获取第 $PAGE 页数据..."
  cloudsmith ls packages "$ORG/$REPO" --page=$PAGE  --output-format=json > packages.json

  # 判断本页是否有包数据
  count=$(jq '.data | length' packages.json)
  if [[ "$count" -eq 0 ]]; then
    echo "🚫 当前页无数据，停止分页。"
    break
  fi

  # 遍历当前页的包
  jq -c '.data[]' packages.json | while read -r pkg; do
    slug=$(echo "$pkg" | jq -r '.slug')
    version=$(echo "$pkg" | jq -r '.version')
    uploaded=$(echo "$pkg" | jq -r '.uploaded_at')
    identifier=$(echo "$pkg" | jq -r '.slug_perm')

    echo "🔍 检测包: $slug@$version 上传时间: $uploaded"

    if [[ "$uploaded" < "$CUTOFF_DATE" ]]; then
      echo "🗑 准备删除包: $slug@$version (ID: $identifier) 上传于 $uploaded"
      if $DRY_RUN; then
        echo "⚠️ Dry-Run 模式，仅打印不删除: $ORG/$REPO/$identifier"
      else
        if ! cloudsmith delete "$ORG/$REPO/$identifier" -y; then
          echo "❌ 删除失败: $ORG/$REPO/$identifier"
        fi
      fi
    else
      echo "✅ 保留包: $slug@$version 上传于 $uploaded"
    fi
  done

  # 判断是否还有下一页
  total_pages=$(jq '.meta.pagination.page_max' packages.json)
  if [[ "$PAGE" -ge "$total_pages" ]]; then
    HAS_MORE=false
  else
    PAGE=$((PAGE + 1))
  fi
done

echo "✅ 清理完成！"
