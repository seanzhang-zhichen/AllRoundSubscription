#!/usr/bin/env python3
"""
微信登录调试工具
用于排查微信登录40029错误
"""
import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.services.wechat import wechat_service
from app.core.logging import get_logger

logger = get_logger(__name__)


async def debug_wechat_config():
    """检查微信配置"""
    print("=" * 50)
    print("微信配置检查")
    print("=" * 50)
    
    print(f"WECHAT_APP_ID: {settings.WECHAT_APP_ID}")
    print(f"WECHAT_APP_SECRET: {'*' * len(settings.WECHAT_APP_SECRET) if settings.WECHAT_APP_SECRET else '未设置'}")
    
    if not settings.WECHAT_APP_ID:
        print("❌ WECHAT_APP_ID 未设置")
        return False
    
    if not settings.WECHAT_APP_SECRET:
        print("❌ WECHAT_APP_SECRET 未设置")
        return False
    
    print("✅ 微信配置检查通过")
    return True


async def test_wechat_api_connectivity():
    """测试微信API连通性"""
    print("\n" + "=" * 50)
    print("微信API连通性测试")
    print("=" * 50)
    
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 测试微信API基础连通性
            url = "https://api.weixin.qq.com/sns/jscode2session"
            params = {
                "appid": "test",
                "secret": "test", 
                "js_code": "test",
                "grant_type": "authorization_code"
            }
            
            response = await client.get(url, params=params)
            data = response.json()
            
            print(f"微信API响应状态码: {response.status_code}")
            print(f"微信API响应内容: {data}")
            
            # 预期会返回40013错误（无效AppID），说明API可达
            if "errcode" in data and data["errcode"] == 40013:
                print("✅ 微信API连通性正常")
                return True
            else:
                print("⚠️ 微信API响应异常")
                return False
                
    except Exception as e:
        print(f"❌ 微信API连通性测试失败: {str(e)}")
        return False


async def simulate_code_validation(test_code: str = None):
    """模拟code验证"""
    print("\n" + "=" * 50)
    print("Code验证模拟测试")
    print("=" * 50)
    
    if not test_code:
        # 生成一个模拟的无效code用于测试
        test_code = "invalid_test_code_" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    print(f"测试Code: {test_code}")
    
    try:
        result = await wechat_service.code_to_session(test_code)
        print(f"✅ Code验证成功: {result}")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Code验证失败: {error_msg}")
        
        # 分析错误类型
        if "40029" in error_msg or "invalid code" in error_msg.lower():
            print("📝 这是预期的40029错误（无效code）")
            print("💡 建议检查：")
            print("   1. 前端获取的code是否及时传递给后端")
            print("   2. code是否被重复使用")
            print("   3. 前后端时间是否同步")
            return False
        elif "40013" in error_msg:
            print("❌ AppID配置错误")
            return False
        elif "40014" in error_msg:
            print("❌ AppSecret配置错误")
            return False
        else:
            print(f"❌ 其他错误: {error_msg}")
            return False


async def analyze_recent_logs():
    """分析最近的日志"""
    print("\n" + "=" * 50)
    print("最近日志分析")
    print("=" * 50)
    
    log_file = "logs/app.log"
    
    if not os.path.exists(log_file):
        print("❌ 日志文件不存在")
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找最近的微信登录相关日志
        wechat_logs = []
        for line in reversed(lines[-1000:]):  # 只看最近1000行
            if any(keyword in line for keyword in ['微信登录', 'wechat_login', '40029', 'code_to_session']):
                wechat_logs.append(line.strip())
        
        if wechat_logs:
            print("🔍 最近的微信登录相关日志:")
            for log in wechat_logs[:10]:  # 只显示最近10条
                print(f"   {log}")
        else:
            print("ℹ️ 未找到最近的微信登录日志")
            
    except Exception as e:
        print(f"❌ 读取日志文件失败: {str(e)}")


def print_troubleshooting_guide():
    """打印故障排查指南"""
    print("\n" + "=" * 50)
    print("微信登录40029错误排查指南")
    print("=" * 50)
    
    guide = """
🔧 常见原因和解决方案：

1. Code已过期（最常见）
   - 原因：微信小程序code有效期只有5分钟
   - 解决：确保前端获取code后立即传递给后端
   - 检查：前后端时间是否同步

2. Code被重复使用
   - 原因：每个code只能使用一次
   - 解决：确保每次登录都获取新的code
   - 检查：前端是否缓存了旧的code

3. Code格式问题
   - 原因：code包含特殊字符或被截断
   - 解决：检查网络传输过程中code是否完整
   - 检查：URL编码/解码问题

4. 配置问题
   - 原因：AppID或AppSecret配置错误
   - 解决：检查微信小程序后台配置
   - 检查：环境变量是否正确设置

🛠️ 调试步骤：

1. 检查微信小程序后台配置
   - 登录微信公众平台
   - 确认AppID和AppSecret正确
   - 检查服务器域名白名单

2. 检查前端代码
   - 确保每次登录都调用wx.login()获取新code
   - 检查code获取后是否立即发送给后端
   - 添加code获取时间戳日志

3. 检查后端代码
   - 确保接收到code后立即调用微信API
   - 添加详细的时间戳日志
   - 检查code是否被意外修改

4. 网络和时间检查
   - 确保服务器网络正常
   - 检查服务器时间是否准确
   - 测试微信API连通性

📱 前端优化建议：

```javascript
// 推荐的前端登录流程
async function wechatLogin() {
  try {
    // 每次都获取新的code
    const loginRes = await uni.login({
      provider: 'weixin'
    });
    
    if (!loginRes.code) {
      throw new Error('获取微信登录code失败');
    }
    
    console.log('获取code成功，立即发送到后端');
    
    // 立即发送给后端，不要延迟
    const response = await request.post('/auth/login', {
      code: loginRes.code
    });
    
    return response;
  } catch (error) {
    console.error('微信登录失败:', error);
    throw error;
  }
}
```

🔄 重试机制：

如果遇到40029错误，可以实现自动重试：
1. 重新获取微信code
2. 最多重试2-3次
3. 每次重试间隔1-2秒
4. 记录详细的重试日志
"""
    
    print(guide)


async def main():
    """主函数"""
    print("🔍 微信登录调试工具启动")
    print(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 检查配置
    config_ok = await debug_wechat_config()
    
    # 2. 测试API连通性
    api_ok = await test_wechat_api_connectivity()
    
    # 3. 模拟code验证
    if config_ok:
        await simulate_code_validation()
    
    # 4. 分析日志
    await analyze_recent_logs()
    
    # 5. 显示排查指南
    print_troubleshooting_guide()
    
    print("\n" + "=" * 50)
    print("调试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())