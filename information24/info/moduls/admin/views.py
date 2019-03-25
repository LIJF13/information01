import time
from datetime import datetime, timedelta
from flask import request, render_template, current_app, session, redirect, url_for, g, jsonify
from info.models import User, News, Category
from info.response_code import RET
from . import admin_bp
from info.utils.common import get_user_info
from info import constants, db
from info.utils.pic_store import upload_image


# /admin/category_edit
@admin_bp.route('/category_edit', methods=["POST"])
def category_edit():
    """新增分类&编辑分类"""
    """
    1.获取参数
        1.1  cid:分类id， category_name:分类名称
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据cid判断是否有值
        cid有值：编辑分类，根据分类id查询对应分类对应，然后修改分类名称
        cid没有值：创建分类对象，并赋值

        3.1 将上述修改提交到数据库
    4.返回值
    """

    # 1.1  cid:分类id， category_name:分类名称
    cid = request.json.get("cid")
    category_name = request.json.get("category_name")

    # 2.1 非空判断
    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 3.0 根据cid判断是否有值
    if cid:
        # cid有值：编辑分类，
        # 根据分类id查询对应分类对象，然后修改分类名称
        try:
            category = Category.query.get(cid)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类对象异常")

        # 修改分类名称
        if category:
            category.name = category_name

    else:
        # cid没有值：创建分类对象，并赋值
        category_obj = Category()
        category_obj.name = category_name
        # 添加到数据库
        db.session.add(category_obj)

    # 3.1 将上述修改提交到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存分类对象异常")

    return jsonify(errno=RET.OK, errmsg="新增&修改分类成功")


@admin_bp.route("/news_type")
def news_type():
    """展示新闻分类页面"""

    # 查询所有分类数据
    # 获取分类数据
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询分类异常")

    # 对象列表转字典列表
    category_dict_list = []
    for category in categories if categories else []:
        category_dict = category.to_dict()
        category_dict_list.append(category_dict)

    # 将分类对象列表转化成字典列表
    # 移除最新分类
    category_dict_list.pop(0)

    data = {
        "categories": category_dict_list
    }

    return render_template("admin/news_type.html", data=data)


# /admin//news_edit_detail?news_id=新闻id
@admin_bp.route('/news_edit_detail', methods=["POST", "GET"])
def news_edit_detail():
    """展示新闻编辑详情页面&新闻编辑"""

    # GET请求：查询新闻对象数据，查询新闻分类数据，并且给对应分类设置标志位
    if request.method == "GET":

        # 0. 获取新闻id
        news_id = request.args.get("news_id")

        # 1. 新闻对象数据
        if news_id:
            try:
                news = News.query.get(news_id)
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

        # 2. 查询所有分类数据，并且选中新闻对应分类
        try:
             categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类对象异常")

        # 新闻对象转字典
        news_dict = news.to_dict() if news else None

        # 将分类对象转换成字典列表
        category_dict_list = []
        for category in categories if categories else []:
            # 将分类对象转换成字典
            category_dict = category.to_dict()

            # 是否选中该分类，默认是不选中
            category_dict["is_selected"] = False
            # 分类id和新闻对应分类id相等，
            if category.id == news.category_id:
                # 给对应新闻的分类id一个标志
                category_dict["is_selected"] = True

            category_dict_list.append(category_dict)

        # 移除最新分类
        category_dict_list.pop(0)

        # 组织返回参数
        data = {
            "news": news_dict,
            "categories": category_dict_list
        }

        return render_template("admin/news_edit_detail.html", data=data)

    # POST请求：重新编辑新闻各个属性，保存到数据库
    """
    1.获取参数
        1.1 news_id:新闻id，title:新闻标题，category_id：新闻分类id
            digest:新闻摘要，index_image：新闻主图片，content：新闻内容
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据新闻id查询新闻对象news
        3.1 将其各个属性进行修改
        3.2 将上述修改操作提交到数据库
    4.返回值
    """
    # 1.1 news_id:新闻id，title:新闻标题，category_id：新闻分类id
    #             digest:新闻摘要，index_image：新闻主图片，content：新闻内容
    news_id = request.form.get("news_id")
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")

    # 2.1 非空判断
    if not all([news_id, title, category_id, digest, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 存在新闻主图片，表示需要修改图片
    image_name = ""
    if index_image:
        # 将图片上传到七牛云
        try:
            image_name = upload_image(index_image.read())
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片到七牛云异常")

    # 3.0 根据新闻id查询新闻对象news
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻对象不存在")

    # 3.1 将其各个属性进行修改
    news.title = title
    news.category_id = category_id
    news.digest = digest
    news.content = content
    # 如果有图片名称，才赋值
    if image_name:
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    # 3.2 将上述修改操作提交到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻对象异常")

    return jsonify(errno=RET.OK, errmsg="编辑新闻成功")


# /admin/news_edit?p=页码&keyword=搜索关键字
@admin_bp.route('/news_edit')
def news_edit():
    """展示新闻编辑页面数据"""

    # 1.获取参数
    p = request.args.get("p", 1)
    # 搜索关键字[可选参数]
    keywords = request.args.get("keywords")

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    # 条件列表
    filter_list = []
    # 如果存在搜索关键字，添加查询条件
    if keywords:
        filter_list.append(News.title.contains(keywords))

    news_list = []
    current_page = 1
    total_page = 1
    try:
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc()) \
            .paginate(p, constants.ADMIN_NEWS_EDIT_PAGE_MAX_COUNT, False)
        # 获取当前页码的所有数据
        news_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="")

    # 对象列表转字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_basic_dict())

    # 组织响应数据
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_edit.html", data=data)


# /admin/news_review_detail?news_id=新闻id
@admin_bp.route('/news_review_detail', methods=["POST", "GET"])
def news_review_detail():
    """新闻审核详情页面逻辑"""

    # GET请求：查询新闻详情数据，返回详情页面
    if request.method == "GET":
        # 查询新闻详情数据
        news_id = request.args.get("news_id")
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
        # 新闻对象转换成字典
        news_dict = news.to_dict() if news else None

        data = {
            "news": news_dict
        }
        return render_template("admin/news_review_detail.html", data=data)

    # POST请求：新闻审核的逻辑

    """
    1.获取参数
        1.1 news_id：新闻id，action:通过&拒绝的行为，reason:拒绝原因 [可选参数]
    2.校验参数
        2.1 非空判断
        2.2 action in ["accept", "reject"]
    3.逻辑处理
        3.0 根据news_id查询新闻对象news
        3.1 根据action判断行为
        通过：news.status = 0
        
        拒绝：news.status = -1  
             news.reason = reason 
        3.2 将数据提交到数据库
    4.返回值
        操作成功
    """

    # 1.1 news_id：新闻id，action:通过&拒绝的行为，reason:拒绝原因 [可选参数]
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    reason = request.json.get("reason")

    # 2.1 非空判断
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 2.2 action in ["accept", "reject"]
    if action not in ["accept", "reject"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.0 根据news_id查询新闻对象news
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 3.1 根据action判断行为
    if action == "accept":
        # 通过：news.status = 0
        news.status = 0
    else:
        # 拒绝：news.status = -1
        #      news.reason = reason
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="请输入拒绝原因")

        # 审核未通过
        news.status = -1
        # 设置未通过的原因
        news.reason = reason

    # 3.2 将数据提交到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻状态异常")

    return jsonify(errno=RET.OK, errmsg="OK")

# /admin/news_review?p=页码
@admin_bp.route('/news_review')
def news_review():
    """新闻审核页面新闻列表数据展示"""

    # 获取页面参数，并且进行参数校验
    p = request.args.get("p", 1)

    # 获取搜索关键字
    keywords = request.args.get("keywords")

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    news_list = []
    current_page = 1
    total_page = 1

    # 查询条件列表  默认条件：查询未审核&审核未通过的新闻
    filter_list = [News.status != 0]

    if keywords:
        # 新闻的标题包含搜索关键字
        filter_list.append(News.title.contains(keywords))

    try:
        # News.status != 0 表示未审核&审核未通过的新闻
        paginate = News.query.filter(*filter_list).order_by(News.create_time.desc())\
            .paginate(p, constants.ADMIN_NEWS_REVIEW_PAGE_MAX_COUNT, False)

        # 获取当前页码的所有数据
        news_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="")

    # 新闻对象列表转字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_review_dict())

    # 组织响应数据
    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_review.html", data=data)


# /admin/user_list?p=页码
@admin_bp.route('/user_list')
def user_list():
    """查询用户列表数据"""

    # 获取参数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user_list = []
    current_page = 1
    total_page = 1
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc())\
            .paginate(p, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        # 获取当前页码的所有数据
        user_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户列表数据异常")

    # 用户对象列表转字典列表
    user_dict_list = []
    for user in user_list if user_list else []:
        user_dict_list.append(user.to_admin_dict())

    # 组织响应数据
    data = {
        "users": user_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/user_list.html", data=data)


@admin_bp.route('/user_count')
def user_count():


    # 1.查询总人数
    total_count = 0
    try:
        # User.is_admin == False:查询非管理员用户
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询月新增数
    """
    tm_year=2019, tm_mon=3, tm_mday=15, tm_hour=15, tm_min=50, tm_sec=50, tm_wday=4, tm_yday=74, tm_isdst=0    月起始时间： 2019-01-01  -- 今天
    月起始时间： 2019-03-01  -- 2019-03-15
    月起始时间： 2019-04-01 -- xxx
    月起始时间： 2020-04-01 -- xxx
    """
    mon_count = 0
    try:
        # 获取当前系统时间
        now = time.localtime()

        # 每一个月的起始时间, 字符串数据
        mon_begin = '%d-%02d-01' % (now.tm_year, now.tm_mon)

        # strptime(): 将`字符串`转换成 `时间格式`
        mon_begin_date = datetime.strptime(mon_begin, '%Y-%m-%d')

        #  用户创建时间 >= 每一个月的起始时间  ： 表示月新增人数
        #  2019-03-01  -- 2019-03-15
        mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询日新增数
    """
     日起始时间： 2019-03-15 00：00 ~ 2019-03-15 23：59
    """
    day_count = 0
    try:
        # 2019-03-15 00：00 一天的开始时间
        day_begin = '%d-%02d-%02d' % (now.tm_year, now.tm_mon, now.tm_mday)
        # 将字符串转换成时间格式
        day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')

        #  用户的创建时间 >  今天的起始时间 ： 表示日新增人数
        #  2019-03-15 15：56 > 2019-03-15 00：00
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)


    # 查询图表信息
    # 获取到当天 2019-03-15 00:00:00时间
    now_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    # 定义空数组，保存数据
    active_date = []
    active_count = []

    """
    begin_date = now_date - timedelta(days=i)

    当前时间： 2019-03-15 00：00
    一天的开始时间：2019-03-15 00：00 - 0天 等于 2019-03-15 00：00
    一天的结束时间： 一天的开始时间 +  1天
    一天的结束时间：2019-03-15 00：00 + 1天 等于 2019-03-15 23：59
    
    
    下一天的开始时间：2019-03-15 00：00 - 1天 等于 2019-03-14 00：00
    下一天的结束时间：2019-03-14 00：00 + 1天 等于：2019-03-14 23：59
    
    下下一天的开始时间：2019-03-15 00：00 - 2天 等于 2019-03-13 00：00
    下下一天的结束时间：2019-03-13 00：00 + 1天 等于：2019-03-13 23：59
     .
     .
     .
     开始时间-结束时间：2019-03-12 00：00  ~ 2019-03-12 23：59
    ..
    .
    开始时间-结束时间：2019-02-15 00：00  ~ 2019-02-15 23：59

    

    """

    # 依次添加数据，再反转
    for i in range(0, 31):  # 0 1 2...30
        # 每一天的起始时间 2019-03-15 00：00i
        begin_date = now_date - timedelta(days=i)

        # 每一天的结束时间 ==  起始时间 + 1天
        # end_date = now_date - timedelta(i) + timedelta(days=1)
        # end_date =  begin_date +  timedelta(days=1)
        end_date = begin_date + timedelta(days=1)

        # 将每一天的时间添加到列表中
        active_date.append(begin_date.strftime('%Y-%m-%d'))

        count = 0
        try:
            #  最后一次登录时间 > 一天的开始时间
            #  最后一次登录时间 < 一天的结束时间
            #  一天的开始时间 < 最后一次登录时间 < 一天的结束时间
            # 2019-03-15 00：00 < 最后一次登录时间 < 2019-03-15 23：59
            # 一天的用户活跃量
            count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                      User.last_login < end_date).count()
        except Exception as e:
            current_app.logger.error(e)
        # 添加每一天的用户活跃量
        active_count.append(count)

    # 将数据反转
    active_date.reverse()
    active_count.reverse()

    data = {"total_count": total_count, "mon_count": mon_count, "day_count": day_count, "active_date": active_date,
            "active_count": active_count}

    return render_template('admin/user_count.html', data=data)


# /admin/index  --> 管理员后台首页
@admin_bp.route('/index')
@get_user_info
def admin_index():
    """展示管理员后台首页"""

    # 查询管理员用户信息
    user = g.user

    data = {
        "user_info": user.to_dict() if user else None
    }

    return render_template("admin/index.html", data=data)


# /admin/login  --> 管理员用户登录接口
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """返回管理员页面&管理员登录接口"""

    # GET请求：返回管理员登录页面
    if request.method == "GET":

        # 管理员用户登录优化：当管理员已经登录成功，再次访问admin/login，就不再展示登录页面，而是直接引导进入管理员首页

        # 获取用户id
        user_id = session.get("user_id")
        # 表示是否是管理员
        is_admin = session.get("is_admin", False)

        # 如果用户已经登录同时登录的用户是管理员，直接进入后台首页
        if user_id and is_admin is True:
            # admin.admin_index表示： admin蓝图名称下面的admin_index方法
            return redirect(url_for("admin.admin_index"))
        else:
            # 进入管理员登录页面
            return render_template("admin/login.html", data={})

    # POST请求：管理员登录逻辑

    """
    1.获取参数
        1.1 username:管理员账号，password未加密密码
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据username查询管理用户是否存在
        3.1 验证密码是否一致
        3.2 不一致： 提示密码填写错误
        3.3 一致：记录管理员用户登录信息
    4.返回值
        登录成功
    """

    # 1.1 username:管理员账号，password未加密密码
    username = request.form.get("username")
    password = request.form.get("password")

    # 2.1 非空判断
    if not all([username, password]):
        return render_template("admin/login.html", data={"errmsg": "参数不足"})


    # 3.0 根据username查询管理用户是否存在
    admin_user = None  # type:User
    try:
        admin_user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", data={"errmsg": "查询管路员用户异常"})

    if not admin_user:
        return render_template("admin/login.html", data={"errmsg": "管理员用户不存在"})

    # 3.1 验证密码是否一致
    if admin_user.check_password(password) is False:
        # 3.2 不一致： 提示密码填写错误
        return render_template("admin/login.html", data={"errmsg": "密码填写错误"})

    # 3.3 一致：记录管理员用户登录信息
    session["user_id"] = admin_user.id
    session["mobile"] = admin_user.mobile
    session["nick_name"] = admin_user.nick_name

    # 记录管理员用户字段
    session["is_admin"] = admin_user.is_admin

    # TODO: 调整到后台管理首页
    return redirect(url_for("admin.admin_index"))











