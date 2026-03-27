#!/usr/bin/env python3
"""
初始化数据库：插入测试用户（直接用 SQL 来避免 bcrypt 版本问题）。
"""

import asyncio
import sqlite3
from datetime import datetime, UTC

async def seed_users():
    """插入测试用户。"""
    conn = sqlite3.connect("/Users/eric/PycharmProjects/YmmosBackend/sqlmodel.db")
    cursor = conn.cursor()

    # 检查用户是否已存在
    cursor.execute("SELECT COUNT(*) FROM user WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        # 插入测试用户
        # 注意：这些密码需要是已哈希的形式，但我们先用明文演示，在实际登录时通过 API 注册
        print("📝 正在插入测试用户...")
        
        # 插入 admin 用户（仅密码登录）
        cursor.execute("""
            INSERT INTO user (username, email, is_active, totp_enabled, created_by, updated_by, created_at, updated_at)
            VALUES ('admin', 'admin@example.com', 1, 0, 'system', 'system', ?, ?)
        """, (datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))
        
        # 插入 test 用户（密码 + TOTP）
        cursor.execute("""
            INSERT INTO user (username, email, is_active, totp_enabled, totp_secret, created_by, updated_by, created_at, updated_at)
            VALUES ('test', 'test@example.com', 1, 1, 'JBSWY3DPEBLW64TMMQ======', 'system', 'system', ?, ?)
        """, (datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))
        
        # 插入 superuser 用户（密码 + TOTP）
        cursor.execute("""
            INSERT INTO user (username, email, is_active, totp_enabled, totp_secret, created_by, updated_by, created_at, updated_at)
            VALUES ('superuser', 'superuser@example.com', 1, 1, 'JBSWY3DPEBLW64TMMQ======', 'system', 'system', ?, ?)
        """, (datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))
        
        # 插入 GitHub 用户演示
        cursor.execute("""
            INSERT INTO user (username, email, github_id, is_active, created_by, updated_by, created_at, updated_at)
            VALUES ('gh_testuser', 'testuser@github.com', '123456789', 1, 'github_oauth', 'github_oauth', ?, ?)
        """, (datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))
        
        conn.commit()
        print("✅ 测试用户插入成功！")
        print("\n⚠️  重要：这些用户目前还没有设置密码哈希！")
        print("📝 请使用以下方式登录：")
        print("─" * 60)
        print("1️⃣  注册 → 输入用户名 'admin'、密码 'admin123'、邮箱")
        print("2️⃣  完成 TOTP 扫码绑定")
        print("3️⃣  然后即可用 admin / admin123 + TOTP 登录")
        print("─" * 60)
        print("\n或者通过 API 直接注册新用户：")
        print("POST /api/v1/auth/register")
        print('{"username": "newuser", "password": "pass123", "email": "new@example.com"}')
    else:
        print("✅ 测试用户已存在，跳过插入")

    conn.close()

if __name__ == "__main__":
    asyncio.run(seed_users())

