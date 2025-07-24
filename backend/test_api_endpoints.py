#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API端点的脚本
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_get_all_accounts():
    """测试获取所有博主的API"""
    print("=== 测试获取所有博主API ===")
    
    async with aiohttp.ClientSession() as session:
        try:
            # 不带关键词的请求
            async with session.get(f"{BASE_URL}/search/accounts?page=1&page_size=5") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"状态码: {response.status}")
                    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    return True
                else:
                    print(f"请求失败，状态码: {response.status}")
                    text = await response.text()
                    print(f"错误信息: {text}")
                    return False
        except Exception as e:
            print(f"请求异常: {e}")
            return False

async def test_get_accounts_by_platform():
    """测试按平台获取博主的API"""
    print("\n=== 测试按平台获取博主API ===")
    
    async with aiohttp.ClientSession() as session:
        try:
            # 获取微信公众号博主
            async with session.get(f"{BASE_URL}/search/accounts?platforms=weixin&page=1&page_size=3") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"微信公众号博主 - 状态码: {response.status}")
                    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    return True
                else:
                    print(f"请求失败，状态码: {response.status}")
                    text = await response.text()
                    print(f"错误信息: {text}")
                    return False
        except Exception as e:
            print(f"请求异常: {e}")
            return False

async def test_search_with_keyword():
    """测试关键词搜索的API"""
    print("\n=== 测试关键词搜索API ===")
    
    async with aiohttp.ClientSession() as session:
        try:
            # 搜索包含"账号"的博主
            async with session.get(f"{BASE_URL}/search/accounts?keyword=账号&page=1&page_size=3") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"关键词搜索 - 状态码: {response.status}")
                    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    return True
                else:
                    print(f"请求失败，状态码: {response.status}")
                    text = await response.text()
                    print(f"错误信息: {text}")
                    return False
        except Exception as e:
            print(f"请求异常: {e}")
            return False

async def main():
    """主测试函数"""
    print("开始测试API端点...")
    print("注意：此测试需要后端服务运行在 http://localhost:8000")
    
    # 测试获取所有博主
    success1 = await test_get_all_accounts()
    
    # 测试按平台获取博主
    success2 = await test_get_accounts_by_platform()
    
    # 测试关键词搜索
    success3 = await test_search_with_keyword()
    
    print(f"\n=== API测试结果 ===")
    print(f"获取所有博主API: {'✓' if success1 else '✗'}")
    print(f"按平台获取博主API: {'✓' if success2 else '✗'}")
    print(f"关键词搜索API: {'✓' if success3 else '✗'}")
    
    if all([success1, success2, success3]):
        print("\n所有API测试通过！")
    else:
        print("\n部分API测试失败，请检查后端服务是否正常运行。")

if __name__ == "__main__":
    asyncio.run(main())