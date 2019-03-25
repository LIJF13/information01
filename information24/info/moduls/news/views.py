from info.models import User, News, Category, Comment, CommentLike
from info.response_code import RET
from info import constants, db
from . import news_bp
from flask import render_template, session, current_app, jsonify, g, request
from info.utils.common import get_user_info


@news_bp.route('/user_follow', methods=['POST'])
@get_user_info
def user_follow():
    """关注、取消关注的后端逻辑实现"""

    """
    1.获取参数
        1.1 user_id:作者id，user:登录用户，action:关注&取消关注的行为
    2.校验参数
        2.1 非空判断
        2.2 action in ["follow", "unfollow"]
    3.逻辑处理
        3.0 根据作者user_id获取author作者对象
        3.2 根据action行为判断是否关注
        关注：将作者添加到用户的关注列表中
        取消关注：将作者从关注列表中移除
        3.3 将上述修改操作提交到数据库
    4.返回值
    """
    # 1.1 user_id:作者id，user:登录用户，action:关注&取消关注的行为
    user_id = request.json.get("user_id")
    action = request.json.get("action")
    # 当前登录用户
    user = g.user

    # 2.1 非空判断
    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 action in ["follow", "unfollow"]
    if action not in ["follow", "unfollow"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 3.0 根据作者user_id获取author作者对象
    try:
        author = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询作者对象异常")

    if not author:
        return jsonify(errno=RET.NODATA, errmsg="作者不存在")

    """
    关注：   author.followers.append(user)
    取消关注：author.followers.remove(user)
    
    """

    # 3.2 根据action行为判断是否关注
    if action == "follow":
        # 关注：将作者添加到用户的关注列表中
        if author in user.followed:
            return jsonify(errno=RET.DATAEXIST, errmsg="不能重复关注")
        else:
            user.followed.append(author)

    else:
        # 取消关注：将作者从关注列表中移除
        if author not in user.followed:
            return jsonify(errno=RET.NODATA, errmsg="关注关系不存在")
        else:
            # 将作者从关注列表移除
            user.followed.remove(author)

    # 3.3 将上述修改操作提交到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    return jsonify(errno=RET.OK, errmsg="关注&取消关注成功")


@news_bp.route('/comment_like', methods=['POST'])
@get_user_info
def comment_like():
    """评论点赞/取消点赞接口实现"""

    """
    1.获取参数
        1.1 user:当前登录的用户对象，comment_id:评论id，action:点赞、取消点赞行为
    2.校验参数
        2.1 非空判断
        2.2 action in ["add", "remove"]
    3.逻辑处理
        3.1 根据comment_id查询出评论对象
        3.2 根据user.id和comment_id 查询出评论点赞对象 ---> commentLike_obj
        3.3 根据action行为判断点赞&取消点赞
        点赞：
        3.3.1 判断commentLike_obj不存在的情况
        3.3.2 创建CommentLike类的对象，并且给其各个属性赋值，保存到数据库
        
        取消点赞： 
        3.3.3 判断commentLike_obj存在
        3.3.4 将评论点赞对象从数据库删除，并提交到数据库
 
    4.返回值
    """

    # 1.1 user:当前登录的用户对象，comment_id:评论id，action:点赞、取消点赞行为
    param_dict = request.json
    comment_id = param_dict.get("comment_id")
    action = param_dict.get("action")
    user = g.user
    # 2.1 非空判断
    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 2.2 action in ["add", "remove"]
    if action not in ["add", "remove"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数字符串错误")

    # 3.1 根据comment_id查询出评论对象
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询评论对象异常")

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论不存在，不允许点赞")

    # 3.2 根据user.id和comment_id 查询出评论点赞对象 ---> commentLike_obj
    # 查询条件：当前登录的用户对于当前这条评论点过赞
    try:
        commentLike_obj = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                   CommentLike.user_id == user.id
                                                   ).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询评论点赞对象异常")


    # 3.3 根据action行为判断点赞&取消点赞
    # 点赞：
    if action == "add":
        # 3.3.1 判断commentLike_obj不存在的情况
        if not commentLike_obj:
            # 3.3.2 创建CommentLike类的对象，并且给其各个属性赋值，保存到数据库
            commentlike = CommentLike()
            # 当前登录的用户点的赞
            commentlike.user_id = user.id
            # 点赞的就是当前评论
            commentlike.comment_id = comment_id

            # 将评论对象上的点赞数据量累加
            comment.like_count += 1

            # 添加到数据库会话对象中
            db.session.add(commentlike)
    else:
        # 取消点赞：
        # 3.3.3 判断commentLike_obj存在
        if commentLike_obj:
            # 3.3.4 将评论点赞对象从数据库删除，并提交到数据库
            db.session.delete(commentLike_obj)

            # 注意：取消点赞，点赞数量-1
            comment.like_count -= 1

    # 将上述操作提交到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存评论对象异常")

    # 4.返回操作成功
    return jsonify(errno=RET.OK, errmsg="OK")


# /news/news_comment 参数是通过请求体携带：{"news_id": 新闻id, parent_id:子评论&主评论...}
@news_bp.route('/news_comment', methods=["POST"])
@get_user_info
def news_comment():
    """发布主/子评论后端接口"""
    """
    1.获取参数
        1.1 news_id:新闻id，user:当前登录的用户对象，content:评论内容，parent_id:区分子评论&主评论
    2.参数校验
        2.1 非空判断
    3.逻辑处理
        3.1 根据新闻id查询新闻对象
        
        3.2 创建评论对象，给其各个属性赋值
        
        3.3 将评论对象保存到数据库
        
    4.返回值
        4.1 将评论对象转化成字典
    """

    # 1.1 news_id:新闻id，user:当前登录的用户对象，content:评论内容，parent_id:区分子评论&主评论
    param_dict = request.json
    news_id = param_dict.get("news_id")
    content = param_dict.get("comment")
    parent_id = param_dict.get("parent_id")
    user = g.user
    # 2.1 非空判断
    if not all([news_id, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 3.1 根据新闻id查询新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在不允许发布评论")

    # 3.2 创建评论对象，给其各个属性赋值
    comment_obj = Comment()
    # 当前登录的用户发布的评论
    comment_obj.user_id = user.id
    # 评论属于那条新闻
    comment_obj.news_id = news.id
    # 评论内容
    comment_obj.content = content

    # 区分子、主评论
    if parent_id:
        # 子评论
        comment_obj.parent_id = parent_id

    # 3.3 将评论对象保存到数据库
    try:
        db.session.add(comment_obj)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 4.1 将评论对象转化成字典
    comment_dict = comment_obj.to_dict() if comment_obj else None

    return jsonify(errno=RET.OK, errmsg="发布评论成功", data=comment_dict)


# /news/news_collect  参数是通过请求体携带：{"news_id": 新闻id, action:行为...}
@news_bp.route('/news_collect', methods=["POST"])
@get_user_info
def news_collect():
    """点击收藏/取消收藏后端接口"""

    """
    1.获取参数
        1.1 news_id:当前新闻id， action:收藏、取消收藏的行为，user:当前登录的用户对象
    2.参数校验
        2.1 非空判断
        2.2 action in ["collect", "cancel_collect"]
    3.逻辑处理
        3.1 根据新闻id查询当前新闻对象news
        3.2 判断新闻是否存在
        3.3 根据行为决定是收藏还是取消收藏
        收藏： 将新闻添加到当前用户的收藏列表中: user.collection_news.append(news)
        取消收藏：将新闻从到当前用户的收藏列表中移除: user.collection_news.remove(news)
        3.4 将上述修改操作保存到数据库中
    4.返回值
        收藏、取消收藏成功
    """

    # 1.1 news_id:当前新闻id， action:收藏、取消收藏的行为，user:当前登录的用户对象
    param_dict = request.json
    news_id = param_dict.get("news_id")
    action = param_dict.get("action")
    user = g.user

    # 2.1 非空判断
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 2.2 action in ["collect", "cancel_collect"]
    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数格式错误")

    #  3.1 根据新闻id查询当前新闻对象news
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

    #  3.2 判断新闻是否存在
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    #  3.3 根据行为决定是收藏还是取消收藏
    if action == "collect":
        #  收藏： 将新闻添加到当前用户的收藏列表中: user.collection_news.append(news)
        user.collection_news.append(news)

    else:
        #  取消收藏：将新闻从到当前用户的收藏列表中移除: user.collection_news.remove(news)
        user.collection_news.remove(news)

    #  3.4 将上述修改操作保存到数据库中
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 返回操作成功
    return jsonify(errno=RET.OK, errmsg="OK")


# 127.0.0.1:5000/news/10
@news_bp.route('/<string:news_id>')
@get_user_info
def news_detail(news_id):
    """展示新闻详情页面"""

    # ----------------------1.查询用户基本信息展示----------------------
    user = g.user

    # 3.将用户对象转换成字典
    user_dict = user.to_dict() if user else None

    # ----------------------2.查询点击排行数据展示----------------------

    try:
        rank_news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    rank_news_dict_list = []
    # 将新闻对象列表转化成字典列表
    for news in rank_news_list if rank_news_list else []:
        # 将新闻对象转换成字典添加到列表中
        rank_news_dict_list.append(news.to_dict())

    # ----------------------3.查询新闻详情数据展示----------------------
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

    # 将新闻对象转换成字典对象
    news_dict = news.to_dict() if news else None

    # ----------------------4.查询当前登录用户是否收藏当前新闻----------------------
    # 定义一个标志位，默认值False：代表还未收藏，反之
    is_collected = False

    if user:
        # 当前新闻在当前用户的新闻收藏列表中
        if news in user.collection_news:
            is_collected = True

    # ----------------------5.查询当前新闻下的所有评论列表数据----------------------
    comment_list = []
    # Comment.news_id == news_id :当前新闻id是等于评论的新闻id
    # Comment.like_count.desc()：点赞数量降序排序
    try:
        comment_list = Comment.query.filter(Comment.news_id == news_id).\
            order_by(Comment.like_count.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询评论列表异常")

    # ----------------------6.查询当前新闻下的所有评论列表数据----------------------

    # 1. 查询出当前新闻的所有评论，取得所有评论的id —>  list[1,2,3,4,5,6]
    # 所有评论id的列表
    comment_id_list = [comment.id for comment in comment_list]

    # 用户登录成功才查询点赞信息
    commentLike_obj_list = []
    if user:
        try:
            # 2.再通过评论点赞模型(CommentLike)查询当前用户点赞了那几条评论  —>[模型1,模型2...]
            # 条件1：点过赞的评论id必须在所有的评论id列表中
            # 条件2：点过赞的用户id必须等于当前登录的用户id
            # 注意：如果用户没有登录None.id空类型是没有id属性的  NoneType' object has no attribute 'id'
            commentLike_obj_list = CommentLike.query.filter(CommentLike.comment_id.in_(comment_id_list),
                                     CommentLike.user_id == user.id
                                     ).all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询评论点赞对象异常")

    # 3. 遍历上一步的评论点赞模型列表，获取所以点赞过的评论id（comment_like.comment_id）
    # 点过赞的评论id列表
    like_commentid_list = [commentLike.comment_id for commentLike in commentLike_obj_list]

    # 评论对象列表转化成字典列表
    comment_dict_list = []
    # 遍历评论对象，每一个评论对象有自己的id值
    for comment in comment_list if comment_list else []:
        # 评论对象转换成字典
        comment_dict = comment.to_dict()
        # 给条评论添加一个标志位，默认值False表示没有点赞
        comment_dict["is_like"] = False
        # 判断每一个评论对象的id值是否在已经点过赞的评论id列表中，如果在就修改标准位True
        # list = [1,2,3,4,5,6]
        # like_commentid_list = [1, 3, 5]
        # 1 in [1, 3, 5]  ====> comment_dict["is_like"] = True
        # 2 in [1, 3, 5]  ====> comment_dict["is_like"] = False
        # 3 in [1, 3, 5]  ====> comment_dict["is_like"] = True
        if comment.id in like_commentid_list:
            comment_dict["is_like"] = True

        # 将评论字典添加到列表中
        comment_dict_list.append(comment_dict)

    # ----------------------7.查询当前`登录用户`是否关注`新闻作者`----------------------

    """
    user: 当前登录用户
    author: 新闻作者
    
    user.followed: 登录用户的关注列表
    author.followers: 作者的粉丝列表
    
    当前用户user关注新闻作者author的两种表示方法：
        1. author in user.followed
        2. user in author.followers
    """
    # 新闻作者对象
    author = User.query.filter(User.id == news.user_id).first()

    # 定义标志位 默认是没有关注
    is_followed = False

    if user and author:
        # 作者在用户的关注列表中
        if author in user.followed:
            is_followed = True

    # 组织返回数据
    data = {
        "user_info": user_dict,
        "click_news_list": rank_news_dict_list,
        "news": news_dict,
        "is_collected": is_collected,
        "comments": comment_dict_list,
        "is_followed": is_followed
     }

    return render_template("news/detail.html", data=data)