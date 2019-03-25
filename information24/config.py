from redis import StrictRedis
import logging

# 0.自定义项目配置类
class Config(object):
    """
    项目配置基类
    """
    # 开启debug模式
    DEBUG = True

    # mysql数据库相关配置
    # 连接数据库的配置
    SQLALCHEMY_DATABASE_URI = "mysql://root:123456@127.0.0.1:3306/information24"
    # 关闭数据库修改跟踪操作
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 当db.session关闭的时候，自动提交数据， 相当于：db.session.commit()
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    # redis数据库配置
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    # 使用session记得设置加密字符串
    SECRET_KEY = "asldjasldkjal*(**d9s8abk"

    # 将session调整到redis数据库保存的配置信息
    SESSION_TYPE = "redis"
    # 具体保存到那个数据库，redis数据库对象
    # session["key"] = value  ---> 数据保存到1号数据库   session: key valye
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=1)
    # 对session_id需要加密处理
    SESSION_USE_SIGNER = True
    # 不需要永久存储
    SESSION_PERMANENT = False
    # 设置有效存储时间为(单位s)：24小时
    PERMANENT_SESSION_LIFETIME = 86400


class DevelopmentConfig(Config):
    """开发模式的配置信息"""
    # 开启debug模式
    DEBUG = True
    # 设置日志级别为:DEBUG
    LOG_LEVEL = logging.DEBUG


class ProductionConfig(Config):
    """线上模式的配置信息"""
    # 开启debug模式
    DEBUG = False
    # 设置日志级别为: WARNING
    LOG_LEVEL = logging.WARNING


# 提供一个接口给外界调用
# 使用：config_dict["development"] --> DevelopmentConfig
config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}