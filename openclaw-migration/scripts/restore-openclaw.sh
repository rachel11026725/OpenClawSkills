#!/bin/bash
# OpenClaw Restore Script
# 用法: ./restore-openclaw.sh [backup-file.tar.gz]
# 不带参数时，会使用目录中最新的备份文件

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR"

echo "🧠 OpenClaw 恢复脚本"
echo "===================="

# Find backup file
if [ -z "$1" ]; then
  # Find the latest backup file
  BACKUP_FILE=$(find "$BACKUP_DIR" -name "openclaw-backup-*.tar.gz" -exec ls -t {} + 2>/dev/null | head -1)
  if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 未找到备份文件!"
    echo "用法: ./restore-openclaw.sh <backup-file.tar.gz>"
    exit 1
  fi
  echo "📦 找到最新备份: $(basename "$BACKUP_FILE")"
else
  BACKUP_FILE="$1"
  if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 文件不存在: $BACKUP_FILE"
    exit 1
  fi
fi

echo "📦 备份文件: $BACKUP_FILE"
echo ""

# Stop gateway
echo "📦 停止 Gateway..."
openclaw gateway stop

# Restore backup
echo "📦 正在恢复 ~/.openclaw/ ..."
tar -xzf "$BACKUP_FILE" -C ~

# Run doctor
echo "🔍 运行诊断..."
openclaw doctor

# Restart gateway
echo "▶️  启动 Gateway..."
openclaw gateway restart

echo ""
echo "✅ 恢复完成!"
echo ""
echo "验证检查:"
echo "  ✓ openclaw status 查看状态"
echo "  ✓ 检查渠道是否仍然连接"
echo "  ✓ 检查工作区文件是否存在"
