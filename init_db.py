#!/usr/bin/env python3
"""
初始化数据库：创建表结构并插入标准测试用户。
"""

import asyncio
import pyotp
from datetime import datetime, UTC
from sqlmodel.ext.asyncio.session import AsyncSession
from db.session import engine, session_factory
from model.user import User
from dao.user_dao import UserDAO
from service.auth_service import _pwd_ctx  # 使用已有的密码哈希上下文


async def seed_users():
    """插入标准测试用户。"""
    user_dao = UserDAO()
    async with session_factory() as session:
        
        # 用户 1：仅密码登录
        test_user_1 = await user_dao.get_by_username(session, "admin")
        if not test_user_1:
            user_1 = User(
                username="admin",
                password=_pwd_ctx.hash("admin123"),  # 密码：admin123
                email="admin@example.com",
                is_active=True,
                totp_enabled=False,  # 不启用 TOTP
                created_by="system",
                updated_by="system",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            user_1 = await user_dao.create(session, user_1)
            print(f"✅ 创建用户: admin (密码: admin123)")

        # 用户 2：密码 + TOTP 登录
        test_user_2 = await user_dao.get_by_username(session, "test")
        if not test_user_2:
            totp_secret = pyotp.random_base32()
            user_2 = User(
                username="test",
                password=_pwd_ctx.hash("test123"),  # 密码：test123
                email="test@example.com",
                is_active=True,
                totp_secret=totp_secret,
                totp_enabled=True,  # 启用 TOTP
                created_by="system",
                updated_by="system",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            user_2 = await user_dao.create(session, user_2)
            totp_uri = pyotp.TOTP(totp_secret).provisioning_uri(
                name="test",
                issuer_name="YmmosBackend",
            )
            print(f"✅ 创建用户: test (密码: test123)")
            print(f"   TOTP Secret: {totp_secret}")
            print(f"   TOTP URI: {totp_uri}")
            # 生成当前有效的验证码供测试
            totp = pyotp.TOTP(totp_secret)
            print(f"   当前验证码: {totp.now()}")

        # 用户 3：GitHub OAuth（演示用）
        test_user_3 = await user_dao.get_by_username(session, "gh_testuser")
        if not test_user_3:
            user_3 = User(
                username="gh_testuser",
                email="testuser@github.com",
                is_active=True,
                github_id="123456789",
                created_by="github_oauth",
                updated_by="github_oauth",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            user_3 = await user_dao.create(session, user_3)
            print(f"✅ 创建用户: gh_testuser (GitHub OAuth)")

        # 用户 4：演示多因素认证用户
        test_user_4 = await user_dao.get_by_username(session, "superuser")
        if not test_user_4:
            totp_secret = pyotp.random_base32()
            user_4 = User(
                username="superuser",
                password=_pwd_ctx.hash("super123"),  # 密码：super123
                email="superuser@example.com",
                is_active=True,
                totp_secret=totp_secret,
                totp_enabled=True,  # 启用 TOTP
                created_by="system",
                updated_by="system",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            user_4 = await user_dao.create(session, user_4)
            totp = pyotp.TOTP(totp_secret)
            print(f"✅ 创建用户: superuser (密码: super123)")
            print(f"   TOTP Secret: {totp_secret}")
            print(f"   当前验证码: {totp.now()}")

        print("\n📋 测试用户创建完成！")
        print("\n测试账号汇总：")
        print("─" * 60)
        print("1️⃣  账号: admin        密码: admin123        (仅密码登录)")
        print("2️⃣  账号: test         密码: test123         (密码+TOTP)")
        print("3️⃣  账号: superuser    密码: super123        (密码+TOTP)")
        print("4️⃣  账号: gh_testuser  (GitHub OAuth 演示)")
        print("─" * 60)


async def main():
    """主函数。"""
    print("🚀 开始初始化数据库...")
    try:
        # 1. 创建所有表
        from sqlmodel import SQLModel
        print("📦 正在创建数据库表...")
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ 数据库表创建完成")
        
        # 2. 插入测试用户
        await seed_users()
        print("\n✨ 初始化完成！")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        raise
    finally:
        from db.session import close_db
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())

