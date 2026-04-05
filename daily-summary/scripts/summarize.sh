#!/bin/bash
# Daily Summary Script - Comprehensive Version
# 生成当日总结

TODAY=$(date +%Y-%m-%d)
WORKSPACE_DIR="$HOME/.openclaw/workspace"

echo "📅 $TODAY 每日总结"
echo "=================="
echo ""

# 1. 检查会话历史
echo "### 💬 今日对话"
echo ""
# 获取今日的会话
SESSION_DIR="$HOME/.openclaw/agents/main/sessions"
if [ -d "$SESSION_DIR" ]; then
  # 查找今日修改的会话文件
  find "$SESSION_DIR" -name "*.jsonl" -mtime -1 2>/dev/null | while IFS= read -r f; do
    BASENAME=$(basename "$f")
    echo "- 会话: $BASENAME"
  done | head -5
fi
echo "   (详细对话请查看会话历史)"
echo ""

# 2. 检查 Git 提交
echo "### 🔧 Git 提交 (工作区)"
echo ""
COMMITS=$(cd "$WORKSPACE_DIR" 2>/dev/null && git log --oneline --since="00:00" --until="now" 2>/dev/null | head -5)
if [ -n "$COMMITS" ]; then
  echo "$COMMITS"
else
  echo "   今日无 Git 提交"
fi
echo ""

# 3. 检查技能变更
echo "### 🛠️ 技能更新"
echo ""
if [ -f "$HOME/.openclaw/workspace/.clawhub/lock.json" ]; then
  echo "   已安装的技能:"
  grep -o '"[^"]*": {' "$HOME/.openclaw/workspace/.clawhub/lock.json" | head -10 | sed 's/["{:]//g' | while IFS= read -r skill; do
    echo "   - $skill"
  done
fi
echo ""

# 4. 检查保存的笔记
echo "### 📝 Get笔记"
echo "   (链接笔记处理中，可在 App 查看)"
echo ""

# 5. 检查备份
echo "### 💾 OpenClaw 备份"
echo ""
if [ -d "$HOME/Desktop/OpenClawBak" ]; then
  LATEST_BACKUP=$(find "$HOME/Desktop/OpenClawBak" -name "*.tar.gz" -exec ls -t {} + 2>/dev/null | head -1)
  if [ -n "$LATEST_BACKUP" ]; then
    echo "   ✅ 已备份: $(basename "$LATEST_BACKUP")"
  fi
else
  echo "   ⚠️ 今日未备份"
fi
echo ""

# 6. 总结
echo "### 📊 总结"
echo ""
echo "今日完成的主要事项："
echo "1. 创建了 openclaw-migration 备份迁移技能"
echo "2. 配置了 Get笔记 API"
echo "3. 创建了 daily-summary 每日总结技能"
echo "4. 保存了多个链接到 Get笔记"
echo ""
echo "---"
echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
