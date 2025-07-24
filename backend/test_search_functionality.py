#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试搜索功能的脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.search.service import search_service
from app.models.account import Platform

async def test_get_all_accounts():
    """测试获取所有博主功能"""
    print("=== 测试获取所有博主 ===")
    
    try:
        # 获取所有博主
        result = await search_service.get_all_accounts(page=1, page_size=10)
        
        print(f"总数: {result.total}")
        print(f"当前页: {result.page}")
        print(f"每页大小: {result.page_size}")
        print(f"是否有更多: {result.has_more}")
        print(f"博主数量: {len(result.accounts)}")
        
        if result.accounts:
            print("\n博主列表:")
            for i, account in enumerate(result.accounts[:5], 1):
                print(f"{i}. {account.name} ({account.platform}) - {account.follower_count} 关注者")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

async def test_get_accounts_by_platform():
    """测试按平台获取博主功能"""
    print("\n=== 测试按平台获取博主 ===")
    
    try:
        # 获取微信公众号博主
        result = await search_service.get_all_accounts(
            platforms=["weixin"], 
            page=1, 
            page_size=10
        )
        
        print(f"微信公众号博主总数: {result.total}")
        print(f"博主数量: {len(result.accounts)}")
        
        if result.accounts:
            print("\n微信公众号博主列表:")
            for i, account in enumerate(result.accounts[:3], 1):
                print(f"{i}. {account.name} - {account.follower_count} 关注者")
        
        # 获取微博博主
        result = await search_service.get_all_accounts(
            platforms=["weibo"], 
            page=1, 
            page_size=10
        )
        
        print(f"\n微博博主总数: {result.total}")
        print(f"博主数量: {len(result.accounts)}")
        
        if result.accounts:
            print("\n微博博主列表:")
            for i, account in enumerate(result.accounts[:3], 1):
                print(f"{i}. {account.name} - {account.follower_count} 关注者")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

async def test_search_with_keyword():
    """测试关键词搜索功能"""
    print("\n=== 测试关键词搜索 ===")
    
    try:
        # 搜索包含"账号"的博主
        result = await search_service.search_accounts(
            keyword="账号",
            page=1,
            page_size=10
        )
        
        print(f"搜索'账号'的结果总数: {result.total}")
        print(f"博主数量: {len(result.accounts)}")
        
        if result.accounts:
            print("\n搜索结果:")
            for i, account in enumerate(result.accounts[:3], 1):
                print(f"{i}. {account.name} ({account.platform}) - {account.follower_count} 关注者")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("开始测试搜索功能...")
    
    # 测试获取所有博主
    success1 = await test_get_all_accounts()
    
    # 测试按平台获取博主
    success2 = await test_get_accounts_by_platform()
    
    # 测试关键词搜索
    success3 = await test_search_with_keyword()
    
    print(f"\n=== 测试结果 ===")
    print(f"获取所有博主: {'✓' if success1 else '✗'}")
    print(f"按平台获取博主: {'✓' if success2 else '✗'}")
    print(f"关键词搜索: {'✓' if success3 else '✗'}")
    
    if all([success1, success2, success3]):
        print("\n所有测试通过！")
    else:
        print("\n部分测试失败，请检查实现。")

if __name__ == "__main__":
    asyncio.run(main())