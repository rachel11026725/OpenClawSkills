#!/bin/bash
# OpenClaw Backup Script
# 用法: ./backup-openclaw.sh
# 备份文件将保存在 ~/Desktop/OpenClawBak/

DESKTOP_DIR="$HOME/Desktop"
BACKUP_DIR="$DESKTOP_DIR/OpenClawBak"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/openclaw-backup-$TIMESTAMP.tar.gz"

# Skill directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🧠 OpenClaw 备份脚本"
echo "===================="

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Copy restore script to backup directory
echo "📄 复制还原脚本..."
cp "$SCRIPT_DIR/restore-openclaw.sh" "$BACKUP_DIR/"
chmod +x "$BACKUP_DIR/restore-openclaw.sh"

# Backup
echo "📦 正在备份 ~/.openclaw/ ..."
cd ~ || exit
tar -czf "$BACKUP_FILE" .openclaw 2>/dev/null

echo ""
echo "✅ 备份完成!"
echo "📁 位置: $BACKUP_FILE"
echo "📁 大小: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
echo "💡 还原命令: cd $BACKUP_DIR && ./restore-openclaw.sh"
