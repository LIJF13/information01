
# 自定义过滤器
# 1.自定义函数实现需求
from flask import session, current_app, jsonify, g
from info.response_code import RET


def do_rank_class(index):

    if index == 1:
        return "first"
    elif index == 2:
        return "second"
    elif index == 3:
        return "third"
    else:
        return ""



# 需求：发现查询用户基本信息代码在多个地方都需要实现，
# 为了达到代码复用的目的，将这些重复代码封装到装饰器中
"""
使用方式：
@get_user_info
def view_func():
        user = g.user
"""


"""
问题：使用装饰器会改变原有函数的函数名称
解决: 导入functools，
使用 @functools.wraps(view_func)纠正函数名称

"""
import functools


def get_user_info(view_func):

    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):

        # 1.将需要新增的需求实现

        # 1.获取用户id
        user_id = session.get("user_id", None)

        # 会出现db循环导入问题，延迟导入
        from info.models import User

        # 2.根据用户id查询用户对象
        user = None  # type: User
        if user_id:
            try:
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

        # 使用全局的临时g对象存储user对象
        # 只要请求还未结束，就能获取到g对象中的内容
        g.user = user

        # 2.原有视图函数功能再次调用执行
        result = view_func(*args, **kwargs)
        return result

    return wrapper
