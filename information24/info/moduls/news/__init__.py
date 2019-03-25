from flask import Blueprint


# 创建蓝图对象  url访问前缀： url_prefix="/news"
news_bp = Blueprint("news", __name__, url_prefix="/news")

from .views import *