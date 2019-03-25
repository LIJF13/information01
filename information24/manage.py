import pymysql
from flask import current_app
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from info import create_app, db, redis_store
from info.models import User
import logging
pymysql.install_as_MySQLdb()


"""
从`单一职责`原理触发manage文件只去实现项目启动和数据库的迁移，
其他项目配置，app应用相关都应该抽取到专门的文件中
"""

# 调用工厂方法创建app对象
app = create_app("development")

# 6.给项目添加迁移能力
Migrate(app, db)

# 7.创建管理对象
manager = Manager(app)

# 8.使用管理对象添加迁移指令
manager.add_command("db", MigrateCommand)


# 需求：创建管理员用户
# 通过一条命令就能创建管理员用户
# 使用：python3 manage.py createSuperUser  -n "账号" -p "密码"
# 使用：python3 manage.py createSuperUser  --username "账号" --password "密码"
@manager.option('-n', '--username', dest="username")
@manager.option('-p', '--password', dest="password")
def createSuperUser(username, password):
    """创建管理员用户方法"""

    if not all([username, password]):
        return "账号密码不能为空"

    # 创建用户对象，并且给其属性赋值
    user = User()
    user.mobile = username
    user.password = password
    user.nick_name = username
    # 标识用户为管理员
    user.is_admin = True

    # 保存到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

        return "保存管理员用户失败"

    return "创建管理员用户成功"


if __name__ == '__main__':
    # 9.使用管理对象运行项目
    manager.run()