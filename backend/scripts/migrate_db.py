#!/usr/bin/env python3
"""
数据库迁移脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.migrations import migrate_database, check_database_compatibility
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    print("开始数据库迁移...")
    
    # 检查兼容性
    print("检查数据库兼容性...")
    if not await check_database_compatibility():
        print("❌ 数据库兼容性检查失败")
        return False
    
    print("✅ 数据库兼容性检查通过")
    
    # 执行迁移
    print("执行数据库迁移...")
    success = await migrate_database()
    
    if success:
        print("✅ 数据库迁移成功完成")
        return True
    else:
        print("❌ 数据库迁移失败")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n迁移被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"迁移过程中发生错误: {str(e)}")
        sys.exit(1)