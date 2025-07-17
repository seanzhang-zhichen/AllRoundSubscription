#!/bin/bash

# 数据备份和恢复脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
BACKUP_DIR="./backups"
COMPOSE_FILE="docker-compose.prod.yml"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 函数: 数据库备份
backup_database() {
    echo -e "${YELLOW}开始数据库备份...${NC}"
    
    BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql"
    
    if docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U postgres content_aggregator > "$BACKUP_FILE"; then
        echo -e "${GREEN}数据库备份完成: $BACKUP_FILE${NC}"
        
        # 压缩备份文件
        gzip "$BACKUP_FILE"
        echo -e "${GREEN}备份文件已压缩: $BACKUP_FILE.gz${NC}"
        
        return 0
    else
        echo -e "${RED}数据库备份失败!${NC}"
        return 1
    fi
}

# 函数: Redis备份
backup_redis() {
    echo -e "${YELLOW}开始Redis备份...${NC}"
    
    REDIS_BACKUP_FILE="$BACKUP_DIR/redis_backup_$DATE.rdb"
    
    if docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli --rdb "$REDIS_BACKUP_FILE" > /dev/null; then
        echo -e "${GREEN}Redis备份完成: $REDIS_BACKUP_FILE${NC}"
        return 0
    else
        echo -e "${RED}Redis备份失败!${NC}"
        return 1
    fi
}

# 函数: 应用数据备份
backup_app_data() {
    echo -e "${YELLOW}开始应用数据备份...${NC}"
    
    APP_BACKUP_FILE="$BACKUP_DIR/app_data_$DATE.tar.gz"
    
    # 备份日志、配置文件等
    tar -czf "$APP_BACKUP_FILE" \
        --exclude='*.log' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='node_modules' \
        ./app ./config ./scripts 2>/dev/null || true
    
    if [ -f "$APP_BACKUP_FILE" ]; then
        echo -e "${GREEN}应用数据备份完成: $APP_BACKUP_FILE${NC}"
        return 0
    else
        echo -e "${RED}应用数据备份失败!${NC}"
        return 1
    fi
}

# 函数: 数据库恢复
restore_database() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}备份文件不存在: $backup_file${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}开始数据库恢复...${NC}"
    echo -e "${RED}警告: 这将覆盖现有数据库!${NC}"
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}恢复操作已取消${NC}"
        return 1
    fi
    
    # 解压备份文件（如果是压缩的）
    if [[ "$backup_file" == *.gz ]]; then
        temp_file="/tmp/restore_$(basename "$backup_file" .gz)"
        gunzip -c "$backup_file" > "$temp_file"
        backup_file="$temp_file"
    fi
    
    # 停止应用服务
    docker-compose -f "$COMPOSE_FILE" stop api celery-worker celery-beat
    
    # 恢复数据库
    if docker-compose -f "$COMPOSE_FILE" exec -T db psql -U postgres -d content_aggregator < "$backup_file"; then
        echo -e "${GREEN}数据库恢复完成${NC}"
        
        # 重启服务
        docker-compose -f "$COMPOSE_FILE" start api celery-worker celery-beat
        
        # 清理临时文件
        [ -f "$temp_file" ] && rm -f "$temp_file"
        
        return 0
    else
        echo -e "${RED}数据库恢复失败!${NC}"
        
        # 重启服务
        docker-compose -f "$COMPOSE_FILE" start api celery-worker celery-beat
        
        return 1
    fi
}

# 函数: 清理旧备份
cleanup_old_backups() {
    echo -e "${YELLOW}清理 $RETENTION_DAYS 天前的备份文件...${NC}"
    
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.rdb" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
    echo -e "${GREEN}旧备份文件清理完成${NC}"
}

# 函数: 列出备份文件
list_backups() {
    echo -e "${BLUE}可用的备份文件:${NC}"
    echo
    
    echo -e "${YELLOW}数据库备份:${NC}"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | awk '{print $9, $5, $6, $7, $8}' || echo "无数据库备份文件"
    
    echo
    echo -e "${YELLOW}Redis备份:${NC}"
    ls -lh "$BACKUP_DIR"/*.rdb 2>/dev/null | awk '{print $9, $5, $6, $7, $8}' || echo "无Redis备份文件"
    
    echo
    echo -e "${YELLOW}应用数据备份:${NC}"
    ls -lh "$BACKUP_DIR"/app_data_*.tar.gz 2>/dev/null | awk '{print $9, $5, $6, $7, $8}' || echo "无应用数据备份文件"
}

# 函数: 完整备份
full_backup() {
    echo -e "${BLUE}=== 开始完整备份 ===${NC}"
    
    local success=0
    
    # 数据库备份
    if backup_database; then
        ((success++))
    fi
    
    # Redis备份
    if backup_redis; then
        ((success++))
    fi
    
    # 应用数据备份
    if backup_app_data; then
        ((success++))
    fi
    
    # 清理旧备份
    cleanup_old_backups
    
    echo -e "${BLUE}=== 备份完成 ===${NC}"
    echo -e "${GREEN}成功备份 $success/3 个组件${NC}"
    
    if [ $success -eq 3 ]; then
        return 0
    else
        return 1
    fi
}

# 函数: 验证备份
verify_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}备份文件不存在: $backup_file${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}验证备份文件: $backup_file${NC}"
    
    # 检查文件大小
    local file_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null)
    if [ "$file_size" -lt 1024 ]; then
        echo -e "${RED}备份文件太小，可能损坏${NC}"
        return 1
    fi
    
    # 检查SQL备份文件
    if [[ "$backup_file" == *.sql.gz ]]; then
        if gunzip -t "$backup_file" 2>/dev/null; then
            echo -e "${GREEN}SQL备份文件验证通过${NC}"
            return 0
        else
            echo -e "${RED}SQL备份文件损坏${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}备份文件验证通过${NC}"
    return 0
}

# 主函数
main() {
    case "${1:-backup}" in
        "backup"|"full")
            full_backup
            ;;
        "db-backup")
            backup_database
            ;;
        "redis-backup")
            backup_redis
            ;;
        "app-backup")
            backup_app_data
            ;;
        "restore")
            if [ -z "$2" ]; then
                echo -e "${RED}请指定备份文件路径${NC}"
                echo "用法: $0 restore <backup_file>"
                exit 1
            fi
            restore_database "$2"
            ;;
        "list")
            list_backups
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "verify")
            if [ -z "$2" ]; then
                echo -e "${RED}请指定备份文件路径${NC}"
                echo "用法: $0 verify <backup_file>"
                exit 1
            fi
            verify_backup "$2"
            ;;
        *)
            echo "用法: $0 {backup|db-backup|redis-backup|app-backup|restore|list|cleanup|verify}"
            echo
            echo "命令说明:"
            echo "  backup      - 完整备份（默认）"
            echo "  db-backup   - 仅备份数据库"
            echo "  redis-backup - 仅备份Redis"
            echo "  app-backup  - 仅备份应用数据"
            echo "  restore     - 恢复数据库备份"
            echo "  list        - 列出所有备份文件"
            echo "  cleanup     - 清理旧备份文件"
            echo "  verify      - 验证备份文件"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"