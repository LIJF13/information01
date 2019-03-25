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
passport_bp = Blueprint("passport", __name__, url_prefix="/passport")

from .views import *
# from info.moduls.index.views import *

