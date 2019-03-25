from info import db
from info.response_code import RET
from . import profile_bp
from flask import render_template, g, request, jsonify, session, current_app
from info.utils.common import get_user_info
from info.utils.pic_store import upload_image
from info import constants
from info.models import Category, News, User


# /user/followed_list?p=页码
@profile_bp.route('/followed_list')
@get_user_info
def followed_list():

    """查询登录用户关注的用户列表"""

    # 提取页码
    p = request.args.get('p', 1)
    # 当前登录的用户
    User
    user = g.user
    # 校验参数
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user_list = []
    current_page = 1
    total_page = 1
    # 查询`关注用户`列表数据，并进行分页处理
    # 分页处理
    try:
        # 使用lazy=dynamic修饰，当只需要查询数据的时候，返回的是`查询对象`，再调用分页函数即可
        paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)

        # 当前页码所有数据
        user_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 将用户对象列表转换成字典列表
    user_dict_list = []
    for user in user_list if user_list else []:
        # to_review_dict字典方法中有新闻状态，拒绝原因
        user_dict_list.append(user.to_dict())

    # 返回数据
    data = {
        "users": user_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("user/user_follow.html", data=data)




# /user/news_list?p=页码
@profile_bp.route('/news_list')
@get_user_info
def news_list():

    """查询当前作者发布的新闻列表数据"""

    # 提取页码
    p = request.args.get('p', 1)
    user = g.user
    # 校验参数
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    news_list = []
    current_page = 1
    total_page = 1
    # 查询`新闻`列表数据，并进行分页处理
    # 查询条件：新闻是当前登录的用户发布的新闻
    # 分页处理
    try:
        paginate = News.query.filter(News.user_id == user.id).order_by(News.create_time.desc()) \
            .paginate(p, constants.USER_NEWS_PAGE_MAX_COUNT, False)

        # 当前页码所有数据
        news_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 将新闻对象列表转换成字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        # to_review_dict字典方法中有新闻状态，拒绝原因
        news_dict_list.append(news.to_review_dict())

    # 返回数据
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("user/user_news_list.html", data=data)



@profile_bp.route('/news_release', methods=['POST', 'GET'])
@get_user_info
def news_release():
    """展示新闻发布页面&发布新闻"""

    # GET请求：查询分类数据，展示新闻发布页面
    if request.method == "GET":

        # 查询分类数据
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类对象异常")

        # 对象列表转换成字典
        category_dict_list = []
        for category in categories if categories else []:
            category_dict_list.append(category.to_dict())

        # 弹出列表第一个元素，移除最新分类
        category_dict_list.pop(0)

        # 渲染模板
        return render_template("user/user_news_release.html", data={"categories": category_dict_list})

    # POST请求：发布新闻
    """
    1.获取参数
        1.1 title:新闻标题，category_id:分类id，digest:新闻摘要，index_image:新闻主图片,
            content:新闻内容，user:当前登录的用户，source:个人发布
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.1 新建新闻对象，并且给各个属性赋值
        3.2 保存回数据库
    4.返回值
        登录成功
    """

    # 1.1 title:新闻标题，category_id:分类id，digest:新闻摘要，index_image:新闻主图片,
    #             content:新闻内容，user:当前登录的用户，source:个人发布

    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    content = request.form.get("content")
    # 新闻图片是文件数据
    index_image = request.files.get("index_image")
    user = g.user
    source = "个人发布"
    # 2.1 非空判断
    if not all([title, category_id, digest, content, index_image]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 3.0 将图片数据上传到七牛云
    try:
        image_name = upload_image(index_image.read())
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="上传图片数据到七牛云异常")

    # 图片名称没有值
    if not image_name:
        return jsonify(errno=RET.DBERR, errmsg="上传图片数据到七牛云异常")

    #  3.1 新建新闻对象，并且给各个属性赋值
    news = News()
    # 新闻标题
    news.title = title
    # 新闻分类
    news.category_id = category_id
    # 摘要
    news.digest = digest
    # 内容
    news.content = content
    # 注意：拼接完整url地址
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    # 新闻发布的作者
    news.user_id = user.id
    # 新闻来源
    news.source = source
    # 发布的新闻默认处于：审核中
    news.status = 1

    #  3.2 保存回数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 数据库回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻对象异常")

    return jsonify(errno=RET.OK, errmsg="发布新闻成功")


# /user/collection_news?page=1
@profile_bp.route('/collection_news')
@get_user_info
def collection_news():
    """查询登录用户收藏的新闻列表数据"""

    """
    1.获取参数
        1.1 page:当前页码，user:当前登录的用户
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.1 user.collection_news当前用户收藏的新闻（查询对象）
        3.2 在查询对象上调用paginate()方法分页处理
    4.返回值
    """
    # 1.1 page:当前页码，user:当前登录的用户
    page = request.args.get("page", 1)
    user = g.user
    # 2.1 非空判断
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1
    # 3.1 user.collection_news当前用户收藏的新闻（查询对象）
    # 3.2 在查询对象上调用paginate()方法分页处理
    # 使用lazy=dynamic修饰的属性，返回的是一个查询对象
    try:
        paginate = user.collection_news.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)

        # 获取当前页码所有数据
        news_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 将对象列表转换成字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_basic_dict())

    # 组织返回数据
    data = {
        "collections": news_dict_list,
        "current_page": current_page,
        "total_page": total_page

    }

    # 返回收藏页面，返回数据
    return render_template("user/user_collection.html", data=data)


@profile_bp.route('/pass_info', methods=['POST', 'GET'])
@get_user_info
def pass_info():
    """修改密码后端接口"""

    if request.method == "GET":
        return render_template("user/user_pass_info.html")

    # POST请求：修改密码
    """
    1.获取参数
        1.1 user:当前登录的用户对象, old_password:旧密码， new_password:新密码
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 user.check_password(旧密码)，将旧密码验证通过
        3.1 将新密码给用户对象的password属性赋值
        3.2 保存回数据库
    4.返回值
        登录成功
    """
    # 1.1 user:当前登录的用户对象, old_password:旧密码， new_password:新密码
    user = g.user  # type:User
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")

    # 2.1 非空判断
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #  3.0 user.check_password(旧密码)，将旧密码验证通过
    if not user.check_password(old_password):
        return jsonify(errno=RET.DATAERR, errmsg="旧密码填写错误")

    #  3.1 将新密码给用户对象的password属性赋值
    user.password = new_password
    #  3.2 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户密码异常")

    return jsonify(errno=RET.OK, errmsg="修改密码成功")


@profile_bp.route('/pic_info', methods=["POST", "GET"])
@get_user_info
def pic_info():
    """上传图片数据到七牛云"""

    # GET请求：展示修改头像页面
    if request.method == "GET":
        return render_template("user/user_pic_info.html")

    # POST请求：将头像数据保存到七牛云
    """
       1.获取参数
           1.1 avatar：头像数据，user:当前登录的用户对象
       2.校验参数
           2.1 非空判断
       3.逻辑处理
           3.0 读取二进制数据，然后调用七牛云工具方法上传图片
           3.1 修改用户avatar_url属性，保存到数据库
           3.2 完整头像url地址返回
       4.返回值
    """

    # 1.1 avatar：头像数据，user:当前登录的用户对象
    avatar = request.files.get("avatar")
    user = g.user
    # 读取二进制数据
    pic_data = avatar.read()

    # 2.1 非空判断
    if not pic_data:
        return jsonify(errno=RET.NODATA, errmsg="图片数据为空")
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 3.0 读取二进制数据，然后调用七牛云工具方法上传图片
    try:
        pic_name = upload_image(pic_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="七牛云上传图片异常")

    # 3.1 修改用户avatar_url属性，保存到数据库
    # 注意：保存到数据库只是图片名称，如果需要加载图片，只需要：constants.QINIU_DOMIN_PREFIX + pic_name
    if pic_name:
        user.avatar_url = pic_name
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存头像数据到数据库异常")

    # 3.2 完整头像url地址返回
    full_url = constants.QINIU_DOMIN_PREFIX + pic_name

    data = {
        "avatar_url": full_url
    }
    return jsonify(errno=RET.OK, errmsg="上传图片数据到七牛云成功", data=data)


# /user/user_base_info
@profile_bp.route('/user_base_info', methods=["POST", "GET"])
@get_user_info
def user_base_info():
    """展示用户基本资料页面&修改用户基本资料"""

    # 1. 获取用户对象
    user = g.user

    # GET请求：查询用户基本资料，展示用户基本资料页面
    if request.method == "GET":

        data = {
            "user_info": user.to_dict() if user else None
        }
        # 2. 返回模板数据
        return render_template("user/user_base_info.html", data=data)

    # POST请求：修改用户基本资料
    """
    1.获取参数
        1.1 user:当前登录的用户， signature: 个性签名，nick_name：昵称，gender：性别
    2.校验参数
        2.1 非空判断
        2.2 gender in ["MAN", "WOMAN"]
    3.逻辑处理
        3.0 修改当前用户的各个属性，
        3.1 修改session数据，保存到数据库
    4.返回值
        登录成功
    """

    # 1.1 user:当前登录的用户， signature: 个性签名，nick_name：昵称，gender：性别
    param_dict = request.json
    signature = param_dict.get("signature")
    nick_name = param_dict.get("nick_name")
    gender = param_dict.get("gender")

    #  2.1 非空判断
    if not all([signature, nick_name, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #  2.2 gender in ["MAN", "WOMAN"]
    if gender not in ["MAN", "WOMAN"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    #  3.0 修改当前用户的各个属性，
    user.signature = signature
    user.nick_name = nick_name
    user.gender = gender

    #  3.1 修改session数据，保存到数据库
    session["nick_name"] = user.nick_name

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    return jsonify(errno=RET.OK, errmsg="修改用户基本资料成功")


# 127.0.0.1:5000/user/user_info
@profile_bp.route('/user_info')
@get_user_info
def user_info():

    # 登录成功获取用户基本信息
    user = g.user
    data = {
        "user_info": user.to_dict() if user else None
    }
    # 返回个人中心首页模板
    return render_template("user/user.html", data=data)