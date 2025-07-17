#!/usr/bin/env python3
"""
系统部署验证脚本
检查所有组件是否正确部署和配置
"""

import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
import sys
import os
import json
import time
from typing import Dict, Any, List, Tuple
from datetime import datetime

# 颜色输出
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(message: str, color: str = Colors.NC):
    print(f"{color}{message}{Colors.NC}")

def print_success(message: str):
    print_colored(f"✓ {message}", Colors.GREEN)

def print_error(message: str):
    print_colored(f"✗ {message}", Colors.RED)

def print_warning(message: str):
    print_colored(f"⚠ {message}", Colors.YELLOW)

def print_info(message: str):
    print_colored(f"ℹ {message}", Colors.BLUE)


class SystemVerifier:
    """系统验证器"""
    
    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/content_aggregator')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    async def verify_api_health(self) -> bool:
        """验证API健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                # 基础健康检查
                async with session.get(f"{self.api_base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'healthy':
                            self.results.append(("API基础健康检查", True, "API服务正常运行"))
                        else:
                            self.results.append(("API基础健康检查", False, f"API状态异常: {data}"))
                            return False
                    else:
                        self.results.append(("API基础健康检查", False, f"HTTP状态码: {response.status}"))
                        return False
                
                # 详细健康检查
                async with session.get(f"{self.api_base_url}/api/v1/monitoring/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'healthy':
                            self.results.append(("API详细健康检查", True, "所有组件健康"))
                            
                            # 检查各个组件
                            checks = data.get('checks', {})
                            for component, status in checks.items():
                                if status.get('status') == 'healthy':
                                    self.results.append((f"{component}组件检查", True, "组件正常"))
                                else:
                                    self.results.append((f"{component}组件检查", False, f"组件异常: {status.get('error', 'Unknown')}"))
                        else:
                            self.results.append(("API详细健康检查", False, f"系统状态异常: {data}"))
                    else:
                        self.results.append(("API详细健康检查", False, f"HTTP状态码: {response.status}"))
                
                return True
                
        except Exception as e:
            self.results.append(("API健康检查", False, f"连接失败: {str(e)}"))
            return False
    
    async def verify_database(self) -> bool:
        """验证数据库连接和表结构"""
        try:
            conn = await asyncpg.connect(self.db_url)
            
            # 基础连接测试
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                self.results.append(("数据库连接", True, "连接成功"))
            else:
                self.results.append(("数据库连接", False, "连接测试失败"))
                return False
            
            # 检查表是否存在
            tables = ['users', 'accounts', 'articles', 'subscriptions', 'push_records']
            for table in tables:
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                if exists:
                    self.results.append((f"表{table}存在性检查", True, "表存在"))
                else:
                    self.results.append((f"表{table}存在性检查", False, "表不存在"))
            
            # 检查数据库性能
            start_time = time.time()
            await conn.fetchval("SELECT COUNT(*) FROM users")
            query_time = time.time() - start_time
            
            if query_time < 1.0:
                self.results.append(("数据库性能", True, f"查询时间: {query_time:.3f}s"))
            else:
                self.results.append(("数据库性能", False, f"查询时间过长: {query_time:.3f}s"))
            
            await conn.close()
            return True
            
        except Exception as e:
            self.results.append(("数据库验证", False, f"错误: {str(e)}"))
            return False
    
    async def verify_redis(self) -> bool:
        """验证Redis连接和功能"""
        try:
            redis_client = redis.from_url(self.redis_url)
            
            # 基础连接测试
            pong = await redis_client.ping()
            if pong:
                self.results.append(("Redis连接", True, "连接成功"))
            else:
                self.results.append(("Redis连接", False, "Ping失败"))
                return False
            
            # 读写测试
            test_key = "verify_test"
            test_value = "test_value"
            
            await redis_client.set(test_key, test_value, ex=60)
            retrieved_value = await redis_client.get(test_key)
            
            if retrieved_value and retrieved_value.decode() == test_value:
                self.results.append(("Redis读写测试", True, "读写正常"))
                await redis_client.delete(test_key)
            else:
                self.results.append(("Redis读写测试", False, "读写失败"))
            
            # 获取Redis信息
            info = await redis_client.info()
            memory_usage = info.get('used_memory_human', 'Unknown')
            connected_clients = info.get('connected_clients', 0)
            
            self.results.append(("Redis状态", True, f"内存使用: {memory_usage}, 连接数: {connected_clients}"))
            
            await redis_client.close()
            return True
            
        except Exception as e:
            self.results.append(("Redis验证", False, f"错误: {str(e)}"))
            return False
    
    async def verify_monitoring(self) -> bool:
        """验证监控系统"""
        try:
            async with aiohttp.ClientSession() as session:
                # 检查Prometheus指标端点
                async with session.get(f"{self.api_base_url}/api/v1/monitoring/metrics") as response:
                    if response.status == 200:
                        content = await response.text()
                        if 'http_requests_total' in content:
                            self.results.append(("Prometheus指标", True, "指标端点正常"))
                        else:
                            self.results.append(("Prometheus指标", False, "指标内容异常"))
                    else:
                        self.results.append(("Prometheus指标", False, f"HTTP状态码: {response.status}"))
                
                # 检查报警系统
                async with session.get(f"{self.api_base_url}/api/v1/monitoring/alerts") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.results.append(("报警系统", True, f"活跃报警: {data.get('summary', {}).get('active_alerts', 0)}"))
                    else:
                        self.results.append(("报警系统", False, f"HTTP状态码: {response.status}"))
                
                return True
                
        except Exception as e:
            self.results.append(("监控系统验证", False, f"错误: {str(e)}"))
            return False
    
    async def verify_api_endpoints(self) -> bool:
        """验证关键API端点"""
        endpoints = [
            ("/api/v1/auth/login", "POST", "认证端点"),
            ("/api/v1/users/profile", "GET", "用户档案端点"),
            ("/api/v1/subscriptions", "GET", "订阅列表端点"),
            ("/api/v1/search/accounts", "GET", "搜索端点"),
            ("/api/v1/feed", "GET", "动态流端点"),
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                for path, method, description in endpoints:
                    try:
                        if method == "GET":
                            async with session.get(f"{self.api_base_url}{path}") as response:
                                # 401 (未授权) 也算正常，说明端点存在
                                if response.status in [200, 401, 422]:
                                    self.results.append((description, True, f"端点可访问 (状态码: {response.status})"))
                                else:
                                    self.results.append((description, False, f"异常状态码: {response.status}"))
                        elif method == "POST":
                            async with session.post(f"{self.api_base_url}{path}", json={}) as response:
                                # 400, 401, 422 都算正常，说明端点存在
                                if response.status in [200, 400, 401, 422]:
                                    self.results.append((description, True, f"端点可访问 (状态码: {response.status})"))
                                else:
                                    self.results.append((description, False, f"异常状态码: {response.status}"))
                    except Exception as e:
                        self.results.append((description, False, f"请求失败: {str(e)}"))
                
                return True
                
        except Exception as e:
            self.results.append(("API端点验证", False, f"错误: {str(e)}"))
            return False
    
    async def verify_system_resources(self) -> bool:
        """验证系统资源"""
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent < 80:
                self.results.append(("CPU使用率", True, f"{cpu_percent}%"))
            else:
                self.results.append(("CPU使用率", False, f"过高: {cpu_percent}%"))
            
            # 内存使用率
            memory = psutil.virtual_memory()
            if memory.percent < 85:
                self.results.append(("内存使用率", True, f"{memory.percent}%"))
            else:
                self.results.append(("内存使用率", False, f"过高: {memory.percent}%"))
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent < 90:
                self.results.append(("磁盘使用率", True, f"{disk_percent:.1f}%"))
            else:
                self.results.append(("磁盘使用率", False, f"过高: {disk_percent:.1f}%"))
            
            return True
            
        except ImportError:
            self.results.append(("系统资源检查", False, "psutil未安装"))
            return False
        except Exception as e:
            self.results.append(("系统资源检查", False, f"错误: {str(e)}"))
            return False
    
    async def run_all_verifications(self) -> Dict[str, Any]:
        """运行所有验证"""
        print_info("开始系统验证...")
        print()
        
        verifications = [
            ("API健康检查", self.verify_api_health),
            ("数据库验证", self.verify_database),
            ("Redis验证", self.verify_redis),
            ("监控系统验证", self.verify_monitoring),
            ("API端点验证", self.verify_api_endpoints),
            ("系统资源检查", self.verify_system_resources),
        ]
        
        for name, verification_func in verifications:
            print_info(f"正在执行: {name}")
            try:
                await verification_func()
            except Exception as e:
                self.results.append((name, False, f"验证过程异常: {str(e)}"))
            print()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        total_checks = len(self.results)
        passed_checks = sum(1 for _, passed, _ in self.results if passed)
        failed_checks = total_checks - passed_checks
        
        print_colored("=" * 60, Colors.BLUE)
        print_colored("系统验证报告", Colors.BLUE)
        print_colored("=" * 60, Colors.BLUE)
        print()
        
        print_info(f"总检查项: {total_checks}")
        print_success(f"通过: {passed_checks}")
        if failed_checks > 0:
            print_error(f"失败: {failed_checks}")
        print()
        
        # 详细结果
        for check_name, passed, message in self.results:
            if passed:
                print_success(f"{check_name}: {message}")
            else:
                print_error(f"{check_name}: {message}")
        
        print()
        
        # 总体状态
        if failed_checks == 0:
            print_success("✓ 所有检查通过，系统部署成功！")
            overall_status = "success"
        elif failed_checks <= total_checks * 0.2:  # 失败率小于20%
            print_warning("⚠ 大部分检查通过，但有少量问题需要关注")
            overall_status = "warning"
        else:
            print_error("✗ 多项检查失败，系统可能存在严重问题")
            overall_status = "error"
        
        return {
            "status": overall_status,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "success_rate": (passed_checks / total_checks) * 100 if total_checks > 0 else 0,
            "timestamp": datetime.utcnow().isoformat(),
            "details": [
                {
                    "check": check_name,
                    "passed": passed,
                    "message": message
                }
                for check_name, passed, message in self.results
            ]
        }


async def main():
    """主函数"""
    verifier = SystemVerifier()
    
    try:
        report = await verifier.run_all_verifications()
        
        # 保存报告到文件
        report_file = f"verification_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print_info(f"详细报告已保存到: {report_file}")
        
        # 根据结果设置退出码
        if report["status"] == "success":
            sys.exit(0)
        elif report["status"] == "warning":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        print_warning("\n验证被用户中断")
        sys.exit(130)
    except Exception as e:
        print_error(f"验证过程发生异常: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())