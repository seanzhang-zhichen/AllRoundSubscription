#!/bin/bash

# 生产环境部署脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"

echo -e "${BLUE}=== Content Aggregator Production Deployment ===${NC}"

# 检查必要文件
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: $ENV_FILE not found!${NC}"
    echo "Please create the production environment file first."
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: $COMPOSE_FILE not found!${NC}"
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 函数: 备份数据库
backup_database() {
    echo -e "${YELLOW}Creating database backup...${NC}"
    BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U postgres content_aggregator > "$BACKUP_FILE"; then
        echo -e "${GREEN}Database backup created: $BACKUP_FILE${NC}"
    else
        echo -e "${RED}Database backup failed!${NC}"
        return 1
    fi
}

# 函数: 健康检查
health_check() {
    echo -e "${YELLOW}Performing health check...${NC}"
    
    # 等待服务启动
    sleep 30
    
    # 检查API健康状态
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo -e "${GREEN}Health check passed!${NC}"
        return 0
    else
        echo -e "${RED}Health check failed!${NC}"
        return 1
    fi
}

# 函数: 回滚
rollback() {
    echo -e "${YELLOW}Rolling back to previous version...${NC}"
    docker-compose -f "$COMPOSE_FILE" down
    # 这里可以添加更复杂的回滚逻辑
    echo -e "${GREEN}Rollback completed${NC}"
}

# 主部署流程
main() {
    echo -e "${YELLOW}Starting deployment process...${NC}"
    
    # 1. 拉取最新镜像
    echo -e "${YELLOW}Pulling latest images...${NC}"
    docker-compose -f "$COMPOSE_FILE" pull
    
    # 2. 如果服务正在运行，先备份数据库
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        backup_database || {
            echo -e "${RED}Backup failed, aborting deployment${NC}"
            exit 1
        }
    fi
    
    # 3. 停止现有服务
    echo -e "${YELLOW}Stopping existing services...${NC}"
    docker-compose -f "$COMPOSE_FILE" down
    
    # 4. 构建新镜像
    echo -e "${YELLOW}Building new images...${NC}"
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # 5. 启动服务
    echo -e "${YELLOW}Starting services...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # 6. 健康检查
    if health_check; then
        echo -e "${GREEN}Deployment successful!${NC}"
        
        # 显示服务状态
        echo -e "${BLUE}Service status:${NC}"
        docker-compose -f "$COMPOSE_FILE" ps
        
        # 显示日志
        echo -e "${BLUE}Recent logs:${NC}"
        docker-compose -f "$COMPOSE_FILE" logs --tail=20
        
    else
        echo -e "${RED}Deployment failed! Starting rollback...${NC}"
        rollback
        exit 1
    fi
}

# 处理命令行参数
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "backup")
        backup_database
        ;;
    "rollback")
        rollback
        ;;
    "health")
        health_check
        ;;
    "logs")
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
    "status")
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
    *)
        echo "Usage: $0 {deploy|backup|rollback|health|logs|status}"
        exit 1
        ;;
esac