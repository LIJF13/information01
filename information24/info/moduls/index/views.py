from info.models import User, News, Category
from info.moduls.index import index_bp
from info import redis_store
from flask import render_template, current_app, session, jsonify, request, abort, g
# from . import index_bp
from info import constants
# 3.使用蓝图对象装饰视图函数
from info.response_code import RET
from info.utils.common import get_user_info


# /news_list?cid=分类id&page=当前页码&per_page=每一页多少条数据
@index_bp.route('/news_list', methods=["GET"])
def get_news_list():
    """获取首页新闻列表数据接口"""

    """
    1.获取参数
        1.1 cid: 当前分类id，page:当前页码，默认值：1， per_page:每一页多少条数据，默认值：10
    2.参数校验
        2.1 判断cid是否为空
        2.2 将数据进行int强制类型转换
    3.逻辑处理
        3.1 根据cid作为查询条件获取查询对象，再调用paginate方法进行数据分页处理
        3.2 调用分类对象的属性 获取当前页所有数据，当前页码，总页码
        3.3 将新闻对象列表转换成字典列表
    4.返回值
    """

    # 1.1 cid: 当前分类id，page:当前页码，默认值：1， per_page:每一页多少条数据，默认值：10
    param_dict = request.args
    cid = param_dict.get("cid")
    # 当前页码 默认值：1
    page = param_dict.get("page", 1)
    # 每一页多少条数据 默认值：10
    per_page = param_dict.get("per_page", 10)

    # 2.1 判断cid是否为空
    if not cid:
       return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 将数据进行int强制类型转换
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        # cid = 1
        # page = 1
        # per_page = 10
        return jsonify(errno=RET.PARAMERR, errmsg="参数格式有误")

    news_list = []
    current_page = 1
    total_page = 1

    """
    if cid == 1:
        # 最新分类，不是一个分类，只需要根据时间降序排序即可，在分页查询
        paginate = News.query.filter().order_by(News.create_time.desc()).paginate(page, per_page, False)
    else:
        # 其他分类，需要先跟cid分类id过滤查询，在根据时间降序排序，再分页查询
        paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()).paginate(page, per_page, False)
    """

    print("----------")
    # sqllachemy底层 == 进行了重写__eq__方法，返回了查询条件而不是Bool值
    print(News.category_id == cid)

    # 定义查询条件列表，默认条件：查询审核通过的新闻
    filter_list = [News.status == 0]

    if cid != 1:
        # 其他分类，需要先根据cid过滤查询，在根据时间降序排序，再分页查询
        filter_list.append(News.category_id == cid)

    # 3.1 根据cid作为查询条件获取查询对象，再调用paginate方法进行数据分页处理
    # 参数1：当前页码  参数2：每一个多少数据 参数3：关闭错误输出，自己捕获
    try:
        # 返回分页对象
        # *filter_list将列表元素解包
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc()).paginate(page, per_page, False)

        # 3.2 调用分类对象的属性 获取当前页所有数据，当前页码，总页码
        # 当前页码所有数据
        news_list = paginate.items

        # 当前页码
        current_page = paginate.page

        # 总页数
        total_page = paginate.pages

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻列表数据异常")

    # 3.3 将新闻对象列表转换成字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        # 将新闻对象转换成字典添加到列表中
        news_dict_list.append(news.to_dict())

    # 4.返回新闻列表数据
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page

    }
    return jsonify(errno=RET.OK, errmsg="查询新闻列表数据成功", data=data)


@index_bp.route('/')
@get_user_info
def index():
    """新闻首页"""

    #----------------------1.查询用户基本信息展示----------------------

    # 需求：发现查询用户基本信息代码在多个地方都需要实现，
    # 为了达到代码复用的目的，将这些重复代码封装到装饰器中

    # # 1.根据session获取用户user_id
    # user_id = session.get("user_id")
    #
    # user = None
    # # 先定义，再使用 否则：local variable 'user_dict' referenced before assignment
    # user_dict = None
    # if user_id:
    #     # 2.根据user_id查询用户对象
    #     try:
    #         user = User.query.get(user_id)
    #     except Exception as e:
    #         current_app.logger.error(e)
    #         return "查询用户对象异常"

    # 从g对象中读取user对象
    user = g.user

    # 3.将用户对象转换成字典
    """
    if user:
        user_dict = user.to_dict()
    """
    user_dict = user.to_dict() if user else None

    # ----------------------2.查询新闻排行列表数据----------------------

    # order_by 将新闻的浏览量降序排序
    try:
        rank_news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询点击排行数据异常")

    """
    rank_news_list：是一个对象列表 [news_obj1, news_obj2, .....]

    rank_dict_list = [] 
    if rank_news_list:
        for news in rank_news_list:
            news_dict = news.to_dict()
            rank_dict_list.append(news_dict)
    """
    # 将对象列表转换成字典列表
    rank_dict_list = []
    for news in rank_news_list if rank_news_list else []:
        # 将对象转换成字典并且添加到列表中
        rank_dict_list.append(news.to_dict())

    # ----------------------3.查询新闻分类列表数据----------------------
    # 1.查询所有分类数据
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻分类对象异常")

    # 2.将分类对象列表转换成字典列表
    category_dict_list = []
    for category in categories if categories else []:
        # 将分类对象转换成字典添加到列表中
        category_dict_list.append(category.to_dict())


    # 返回模板的同时将查询到的数据一并返回
    """
        数据格式：
        data = {
            "user_info": {
                            "id": self.id,
                            "nick_name": self.nick_name,
                            }
        }
        
        使用： data.user_info.nick_name
              data.rank_news_list -- 字典列表
    
    """
    # 组织返回数据
    data = {
        "user_info": user_dict,
        "click_news_list": rank_dict_list,
        "categories": category_dict_list
    }

    return render_template("news/index.html", data=data)


# 网站自动调用通过/favicon.ico路由请求一张网站图标
@index_bp.route('/favicon.ico')
def get_favicon():
    """

    Function used internally to send static files from the static
        folder to the browser
    内部使用send_static_file方法将静态文件夹中的图片数据发送到浏览器
    """
    # 找到网站图片的静态资源并返回
    return current_app.send_static_file("news/favicon.ico")