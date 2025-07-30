#!/bin/bash

# 数据库同步脚本启动文件

# 检查是否已经安装了所需的Python模块
check_dependencies() {
  echo "正在检查依赖..."
  pip install -q sqlalchemy pymysql
  if [ $? -ne 0 ]; then
    echo "安装依赖失败，请检查网络连接或手动安装：pip install sqlalchemy pymysql"
    exit 1
  fi
}

# 检查配置文件是否存在且已正确配置
check_config() {
  echo "正在检查配置..."
  if [ ! -f "config.py" ]; then
    echo "错误：未找到配置文件 config.py"
    exit 1
  fi
  
  # 检查目标数据库配置是否已修改
  grep -q "用户名.*修改为实际用户名" config.py
  if [ $? -eq 0 ]; then
    echo "警告：请先修改 config.py 中的目标数据库配置"
    exit 1
  fi
}

# 启动同步程序
start_sync() {
  echo "开始启动数据库同步程序..."
  
  # 检查是否需要在后台运行
  if [ "$1" == "-d" ] || [ "$1" == "--daemon" ]; then
    echo "以守护进程方式运行..."
    nohup python sync_db.py > sync_db_output.log 2>&1 &
    echo $! > sync_db.pid
    echo "程序已在后台运行，PID: $(cat sync_db.pid)"
    echo "可使用 'tail -f sync_db.log' 查看日志"
  else
    # 在前台运行
    python sync_db.py
  fi
}

# 停止同步程序
stop_sync() {
  if [ -f "sync_db.pid" ]; then
    PID=$(cat sync_db.pid)
    if ps -p $PID > /dev/null; then
      echo "正在停止数据库同步程序 (PID: $PID)..."
      kill $PID
      rm sync_db.pid
      echo "已停止"
    else
      echo "程序未在运行"
      rm sync_db.pid
    fi
  else
    echo "未找到 PID 文件，程序可能未在运行"
  fi
}

# 显示帮助信息
show_help() {
  echo "数据库同步程序控制脚本"
  echo "用法:"
  echo "  $0 [选项]"
  echo "选项:"
  echo "  start          启动同步程序（前台运行）"
  echo "  start -d       以守护进程方式启动（后台运行）"
  echo "  stop           停止同步程序"
  echo "  restart        重启同步程序"
  echo "  status         查看程序状态"
  echo "  help           显示此帮助信息"
}

# 检查程序状态
check_status() {
  if [ -f "sync_db.pid" ]; then
    PID=$(cat sync_db.pid)
    if ps -p $PID > /dev/null; then
      echo "数据库同步程序正在运行 (PID: $PID)"
      return 0
    else
      echo "程序未在运行，但PID文件存在"
      rm sync_db.pid
      return 1
    fi
  else
    echo "程序未在运行"
    return 1
  fi
}

# 主程序逻辑
case "$1" in
  start)
    check_dependencies
    check_config
    start_sync $2
    ;;
  stop)
    stop_sync
    ;;
  restart)
    stop_sync
    sleep 2
    check_dependencies
    check_config
    start_sync $2
    ;;
  status)
    check_status
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    show_help
    exit 1
    ;;
esac

exit 0 