# class Person(object):
#
#     def __init__(self, name):
#         self.name = name
#
#     def __eq__(self, other):
#         pass
#
#
# if __name__ == '__main__':
#
#     p1 = Person("xiaowang")
#     p2 = Person("xiaoli")
#
#     print(p1 == p2)

    # 单列就是始终只创建一个实例对象，只有一个id地址


"""
问题：使用装饰器会改变原有函数的函数名称
解决: 导入functools，
使用 @functools.wraps(view_func)纠正函数名称

"""
# import functools
#
# def get_user_info(view_func):
#
#     @functools.wraps(view_func)
#     def wrapper(*args, **kwargs):
#         pass
#
#     return wrapper
#
# @get_user_info
# def news():
#     """新闻模块"""
#     pass
#
# @get_user_info
# def user():
#     """用户模块"""
#     pass
#
#
# if __name__ == '__main__':
#     print(news.__name__)
#     print(user.__name__)

import datetime
import random
from info import db
from info.models import User
from manage import app


# 录入1万个测试用户
def add_test_users():
    users = []
    # 获取当前时间
    now = datetime.datetime.now()
    # 生成1w个用户
    for num in range(0, 10000):
        try:
            user = User()
            user.nick_name = "%011d" % num
            user.mobile = "%011d" % num

            user.password_hash = "pbkdf2:sha256:50000$SgZPAbEj$a253b9220b7a916e03bf27119d401c48ff4a1c81d7e00644e0aaf6f3a8c55829"
            #                03-15 - 最大值31天 = 02-15活跃
            #                03-15 - 随机值秒数 = 02-15 ~ 03-15之间任意一个时间点活跃
            #                03-15 - 最小值0 = 03-15活跃
            user.last_login = now - datetime.timedelta(seconds=random.randint(0, 2678400))

            users.append(user)
            print(user.mobile)
        except Exception as e:
            print(e)
    #  开启应用上下文
    with app.app_context():
        # 添加到数据库
        db.session.add_all(users)
        db.session.commit()


if __name__ == '__main__':
    add_test_users()