# 1.导入蓝图类
from flask import Blueprint
"""
1.导入蓝图类
2.创建蓝图对象
3.使用蓝图对象装饰视图函数
4.注册蓝图对象
"""

# 2.创建蓝图对象
# url_prefix: 登录注册模块的url访问前缀
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

from .views import *
# from info.moduls.index.views import *


# 借助请求钩子，在每一次请求之前进行用户权限判断
@admin_bp.before_request
def is_admin_user():
    """判断是否是管理员用户分配不同的逻辑"""

    # 访问管理员登录页面，不需要拦截处理
    if request.url.endswith('/admin/login'):
        pass
    else:
        # 每一次请求之前都进行拦截判断处理
        # 1.用户id
        user_id = session.get("user_id")
        # 2.管理员标志位
        is_admin = session.get("is_admin", False)

        # 如果用户没有登录，或者登录的用户不是管理员，都应该引导到新闻首页[/]
        if not user_id or is_admin is False:
            return redirect(url_for("index.index"))


