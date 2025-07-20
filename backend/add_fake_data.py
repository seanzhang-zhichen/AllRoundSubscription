#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加假数据到数据库的脚本
"""

import sqlite3
import json
from datetime import datetime, timedelta
import random
import string

def generate_random_string(length=10):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_openid():
    """生成微信openid格式的字符串"""
    return 'wx_' + generate_random_string(24)

def generate_fake_users(count=20):
    """生成假用户数据"""
    users = []
    membership_levels = ['free', 'premium']
    
    for i in range(count):
        openid = generate_openid()
        nickname = f"用户{i+1:03d}"
        avatar_url = f"https://example.com/avatar/{i+1}.jpg"
        membership_level = random.choice(membership_levels)
        
        # 如果是premium用户，设置过期时间
        if membership_level == 'premium':
            expire_days = random.randint(30, 365)
            membership_expire_at = datetime.now() + timedelta(days=expire_days)
        else:
            membership_expire_at = None
            
        created_at = datetime.now() - timedelta(days=random.randint(1, 100))
        updated_at = created_at + timedelta(days=random.randint(0, 10))
        
        users.append((
            openid, nickname, avatar_url, membership_level, 
            membership_expire_at, created_at, updated_at
        ))
    
    return users

def generate_fake_accounts(count=15):
    """生成假账号数据"""
    accounts = []
    platforms = ['weixin', 'weibo', 'zhihu', 'bilibili', 'douyin']
    
    for i in range(count):
        platform = random.choice(platforms)
        name = f"{platform}账号{i+1:03d}"
        account_id = f"{platform}_{generate_random_string(8)}"
        avatar_url = f"https://example.com/account_avatar/{i+1}.jpg"
        description = f"这是一个{platform}平台的优质内容账号，专注于分享有价值的内容。"
        follower_count = random.randint(1000, 1000000)
        
        details = {
            "verified": random.choice([True, False]),
            "category": random.choice(["科技", "娱乐", "教育", "生活", "财经"]),
            "tags": random.sample(["热门", "原创", "优质", "专业", "有趣"], k=random.randint(1, 3))
        }
        
        created_at = datetime.now() - timedelta(days=random.randint(1, 200))
        updated_at = created_at + timedelta(days=random.randint(0, 30))
        
        accounts.append((
            name, platform, account_id, avatar_url, description, 
            follower_count, json.dumps(details, ensure_ascii=False), 
            created_at, updated_at
        ))
    
    return accounts

def generate_fake_articles(account_ids, count=100):
    """生成假文章数据"""
    articles = []
    
    for i in range(count):
        account_id = random.choice(account_ids)
        title = f"精彩文章标题 {i+1:03d} - 值得一读的优质内容"
        url = f"https://example.com/article/{generate_random_string(12)}"
        content = f"这是文章{i+1}的详细内容。" * random.randint(10, 50)
        summary = f"这是文章{i+1}的摘要，简要介绍了文章的主要内容和观点。"
        
        publish_time = datetime.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        publish_timestamp = int(publish_time.timestamp())
        
        images = [
            f"https://example.com/image/{i+1}_{j}.jpg" 
            for j in range(random.randint(0, 3))
        ]
        
        details = {
            "read_count": random.randint(100, 10000),
            "like_count": random.randint(10, 1000),
            "comment_count": random.randint(0, 100),
            "share_count": random.randint(0, 50)
        }
        
        created_at = publish_time + timedelta(minutes=random.randint(1, 60))
        updated_at = created_at + timedelta(hours=random.randint(0, 24))
        
        articles.append((
            account_id, title, url, content, summary, publish_time, 
            publish_timestamp, json.dumps(images, ensure_ascii=False), 
            json.dumps(details, ensure_ascii=False), created_at, updated_at
        ))
    
    return articles

def generate_fake_subscriptions(user_ids, account_ids, count=50):
    """生成假订阅数据"""
    subscriptions = []
    used_pairs = set()
    
    for _ in range(count):
        # 确保用户-账号对不重复
        while True:
            user_id = random.choice(user_ids)
            account_id = random.choice(account_ids)
            pair = (user_id, account_id)
            if pair not in used_pairs:
                used_pairs.add(pair)
                break
        
        created_at = datetime.now() - timedelta(days=random.randint(1, 60))
        updated_at = created_at + timedelta(days=random.randint(0, 5))
        
        subscriptions.append((user_id, account_id, created_at, updated_at))
    
    return subscriptions

def generate_fake_push_records(user_ids, article_ids, count=200):
    """生成假推送记录数据"""
    push_records = []
    statuses = ['success', 'failed', 'pending']
    
    for i in range(count):
        user_id = random.choice(user_ids)
        article_id = random.choice(article_ids)
        push_time = datetime.now() - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        status = random.choice(statuses)
        
        error_message = None
        if status == 'failed':
            error_messages = [
                "网络连接超时",
                "用户已取消订阅",
                "推送服务暂时不可用",
                "消息格式错误"
            ]
            error_message = random.choice(error_messages)
        
        created_at = push_time + timedelta(seconds=random.randint(1, 300))
        updated_at = created_at + timedelta(seconds=random.randint(0, 60))
        
        push_records.append((
            user_id, article_id, push_time, status, error_message, 
            created_at, updated_at
        ))
    
    return push_records

def main():
    """主函数"""
    # 连接数据库
    conn = sqlite3.connect('content_aggregator.db')
    cursor = conn.cursor()
    
    try:
        print("开始生成假数据...")
        
        # 1. 添加用户数据
        print("添加用户数据...")
        users = generate_fake_users(20)
        cursor.executemany('''
            INSERT INTO users (openid, nickname, avatar_url, membership_level, 
                             membership_expire_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', users)
        
        # 获取用户ID
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
        print(f"添加了 {len(users)} 个用户")
        
        # 2. 添加账号数据
        print("添加账号数据...")
        accounts = generate_fake_accounts(15)
        cursor.executemany('''
            INSERT INTO accounts (name, platform, account_id, avatar_url, description,
                                follower_count, details, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', accounts)
        
        # 获取账号ID
        cursor.execute("SELECT id FROM accounts")
        account_ids = [row[0] for row in cursor.fetchall()]
        print(f"添加了 {len(accounts)} 个账号")
        
        # 3. 添加文章数据
        print("添加文章数据...")
        articles = generate_fake_articles(account_ids, 100)
        cursor.executemany('''
            INSERT INTO articles (account_id, title, url, content, summary, publish_time,
                                publish_timestamp, images, details, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', articles)
        
        # 获取文章ID
        cursor.execute("SELECT id FROM articles")
        article_ids = [row[0] for row in cursor.fetchall()]
        print(f"添加了 {len(articles)} 篇文章")
        
        # 4. 添加订阅数据
        print("添加订阅数据...")
        subscriptions = generate_fake_subscriptions(user_ids, account_ids, 50)
        cursor.executemany('''
            INSERT INTO subscriptions (user_id, account_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        ''', subscriptions)
        print(f"添加了 {len(subscriptions)} 个订阅关系")
        
        # 5. 添加推送记录数据
        print("添加推送记录数据...")
        push_records = generate_fake_push_records(user_ids, article_ids, 200)
        cursor.executemany('''
            INSERT INTO push_records (user_id, article_id, push_time, status, 
                                    error_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', push_records)
        print(f"添加了 {len(push_records)} 条推送记录")
        
        # 提交事务
        conn.commit()
        print("所有假数据添加完成！")
        
        # 显示统计信息
        print("\n数据库统计信息:")
        tables = ['users', 'accounts', 'articles', 'subscriptions', 'push_records']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count} 条记录")
            
    except Exception as e:
        print(f"添加数据时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()