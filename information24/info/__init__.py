from flask import Flask, session, render_template, g
from flask_sqlalchemy import SQLAlchemy
from redis import StrictRedis
from flask_wtf.csrf import CSRFProtect, generate_csrf
# 调整flask.session的存储位置的工具类
from flask_session import Session
from config import config_dict
import logging
from logging.handlers import RotatingFileHandler
from info.utils.common import do_rank_class, get_user_info


# 当app对象为空的情况，并没有真正做数据库的初始化操作
db = SQLAlchemy()

# redis数据库对象
# 声明数据类型
redis_store = None  # type: StrictRedis


# config_class配置类
def write_log(config_class):
    # 记录日志信息

    # 设置日志的记录等级
    logging.basicConfig(level=config_class.LOG_LEVEL)  # 调试debug级

    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小100M、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)

    # 创建日志记录的格式：               日志等级      输入日志信息的文件名 行数   日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')

    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)

    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


# 将app的创建封装到:工厂方法中
# config_name = development
def create_app(config_name):

    # 1.创建app对象
    app = Flask(__name__)

    # 获取项目配置类
    # config_dict["development"] -- DevelopmentConfig -- 开发模式下的app对象
    # config_dict["production"] -- ProductionConfig --  生产模式下的app对象
    config_class = config_dict[config_name]
    # 赋予app不同的配置信息
    app.config.from_object(config_class)

    # 记录日志
    write_log(config_class)

    # 2.懒加载，延迟初始化
    # 当app存在的情况，才做真实的数据库初始化操作
    db.init_app(app)

    # 3.创建redis数据库对象
    # decode_responses=True: 能够将bytes类型数据转换成字符串
    # redis_store.set("key","value")  ---> 数据保存到0号数据库
    # 懒加载
    global redis_store
    redis_store = StrictRedis(host=config_class.REDIS_HOST, port=config_class.REDIS_PORT, decode_responses=True)

    # 4.给项目添加csrf保护机制
    # 1.提取cookie中的csrf_token的值
    # 2.提取form表单或者ajax请求头中携带的csrf_token值
    # 3.自动对比这两个值是否一致
    CSRFProtect(app)

    # 在每一次请求之后,借助响应对象统一设置csrf_token值给浏览器保存
    @app.after_request
    def set_csrf_token(response):
        # 1.生成csrf_token随机值
        csrf_token = generate_csrf()
        # 2.借助响应对象设置cookie
        # csrf_token="xaoisjdosajdosahjdsaoid888"
        response.set_cookie("csrf_token", csrf_token)
        # 3.返回响应对象
        return response

    # 捕获全局的404异常信息统一引导到404页面
    @app.errorhandler(404)
    @get_user_info
    def handler_404notfuond(err):

        # 从装饰封装的g对象中获取用户对象
        user = g.user
        user_dict = user.to_dict() if user else None
        data = {
            "user_info": user_dict
        }
        # 捕获404异常，统一返回404页面
        return render_template("news/404.html", data=data)


    # 5.将flask.session的存储位置从服务器 `内存` 调整到 `redis` 数据库
    Session(app)

    # 延迟导入，解决循环导包问题
    # 注册首页蓝图对象
    from info.moduls.index import index_bp
    app.register_blueprint(index_bp)

    # 登录注册蓝图对象
    from info.moduls.passport import passport_bp
    app.register_blueprint(passport_bp)

    # 新闻详情蓝图对象
    from info.moduls.news import news_bp
    app.register_blueprint(news_bp)

    # 个人中心蓝图对象
    from info.moduls.profile import profile_bp
    app.register_blueprint(profile_bp)

    # 新闻管理后台蓝图对象
    from info.moduls.admin import admin_bp
    app.register_blueprint(admin_bp)

    # 添加自定义的过滤器
    app.add_template_filter(do_rank_class, "rank_class")

    # 返回app对象
    return app


