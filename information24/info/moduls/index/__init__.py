# 1.导入蓝图类
from flask import Blueprint
"""
1.导入蓝图类
2.创建蓝图对象
3.使用蓝图对象装饰视图函数
4.注册蓝图对象
"""

# 2.创建蓝图对象
index_bp = Blueprint("index", __name__)

from .views import *
# from info.moduls.index.views import *


