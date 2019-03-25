from flask import request, abort, make_response, current_app, jsonify, session
from info.utils.captcha.captcha import captcha
from info import redis_store, db
from info import constants
from . import passport_bp
from info.response_code import RET
import re, random
from info.models import User
from info.lib.yuntongxun.sms import CCP
from datetime import datetime


# /passport/login_out
@passport_bp.route('/login_out', methods=["POST"])
def login_out():
    """退出登录后端实现"""

    # 1.将session中键值对数据删除
    session.pop("user_id", "")
    session.pop("nick_name", "")
    session.pop("mobile", "")

    # 退出登录记得清楚管理员权限
    session.pop("is_admin", "")

    return jsonify(errno=RET.OK, errmsg="  ")


# /passport/login 参数通过请求体携带: {"mobile": 18511112222, "password": 123456 }
@passport_bp.route('/login', methods=["POST"])
def login():
    """登录后端接口"""

    """
    1.获取参数
        1.1 mobile:手机号码， password:未加密的密码
    2.参数校验
        
    3.逻辑处理
        3.1 根据手机号码查询用户是否存在
        不存在：提示用户注册
        存在：根据用户对象，校验密码是否正确
        密码不正确：重新输入密码
        3.2 更新最后一次登录时间 [将修改操作保存回数据]
        3.3 使用session记录用户信息
    4.返回值
        4.1 登录成功
    """

    # 1.1 mobile:手机号码， password:未加密的密码
    param_dict = request.json
    mobile = param_dict.get("mobile")
    password = param_dict.get("password")

    # 2.1 非空判断
    if not all([mobile, password]):
        current_app.logger.error("参数不足")
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 手机号码格式判断
    if not re.match(r"1[3578][0-9]{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码格式错误")

    # 3.1 根据手机号码查询用户是否存在
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 不存在：提示用户注册
    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    # 存在：根据用户对象，校验密码是否正确
    if user.check_password(password) is False:
        # 密码不正确：重新输入密码
        return jsonify(errno=RET.DATAERR, errmsg="密码填写错误")

    # 3.2 更新最后一次登录时间 [将修改操作保存回数据]
    # 注意配置数据库字段：SQLALCHEMY_COMMIT_ON_TEARDOWN = True 自动提交数据db.session.commit()
    user.last_login = datetime.now()

    # 将修改操作提交到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")

    # 3.3 使用session记录用户信息
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name

    # 4.1 登录成功
    return jsonify(errno=RET.OK, errmsg="登录成功")


# /passport/register  参数通过请求体携带: {"mobile": 18511112222, "smscode": 123456 ...}
@passport_bp.route('/register', methods=["POST"])
def register():
    """注册的后端接口"""

    """
    1.获取参数
        1.1 mobile:手机号码， smscode: 用户填写短信验证码， password:未加密的密码
    2.参数校验
        2.1 非空判断
        2.2 手机号码格式判断
    3.逻辑处理
        3.1 根据手机号码去redis数据库提取正确的短信验证码值
        短信验证码有值：从redis数据库删除 [避免同一个验证码多次验证码] 
        短信验证码没有值：短信验证码过期了 
        3.2 对比`用户填写短信验证码`和正确的短信验证值是否一致
        3.3 不相等：短信验证码填写错误
        3.4 相等：使用User类创建实例对象，给其各个属性赋值
        3.5 将用户对象保存到数据库
        3.6 注册成功表示登录成功，使用session记录用户信息
    4.返回值
        4.1 返回注册成功
    """

    # 1.1 mobile:手机号码， sms_code: 用户填写短信验证码， password:未加密的密码
    param_dict = request.json
    mobile = param_dict.get("mobile")
    sms_code = param_dict.get("sms_code")
    password = param_dict.get("password")

    # 2.1 非空判断
    if not all([mobile, sms_code, password]):
        current_app.logger.error("参数不足")
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 手机号码格式判断
    if not re.match(r"1[3578][0-9]{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码格式错误")

    #  3.1 根据手机号码去redis数据库提取正确的短信验证码值
    try:
        real_sms_code = redis_store.get("SMS_CODE_%s" % mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询redis中短信验证码异常")

    #  短信验证码有值：从redis数据库删除 [避免同一个验证码多次验证码]
    if real_sms_code:
        redis_store.delete("SMS_CODE_%s" % mobile)
    #  短信验证码没有值：短信验证码过期了
    else:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期")

    #  3.2 对比`用户填写短信验证码`和正确的短信验证值是否一致
    if sms_code != real_sms_code:
        #  3.3 不相等：短信验证码填写错误
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码填写错误")

    #  3.4 相等：使用User类创建实例对象，给其各个属性赋值
    user = User()
    # 昵称
    user.nick_name = mobile
    # 手机号码
    user.mobile = mobile
    # TODO: 密码加密
    # user.set_password_hash(password)
    # 动态添加`password`属性
    user.password = password

    # 最后一次登录时间
    user.last_login = datetime.now()

    #  3.5 将用户对象保存到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 数据库回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户对象异常")

    #  3.6 注册成功表示登录成功，使用session记录用户信息 [提高用户体验]
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    # 4.1 返回注册成功
    return jsonify(errno=RET.OK, errmsg="注册成功")


# /passport/sms_code   参数通过请求体携带: {"mobile": 18511112222, "image_code": 1234 ...}
@passport_bp.route('/sms_code', methods=["POST"])
def send_sms_code():
    """发送短信验证码后端接口"""
    """
    1.获取参数
        1.1 mobile: 手机号码，image_coed:用户填写的图形验证码值， image_code_id: UUID唯一编号
        1.2 数据是通过json格式上传的：request.json
    2.校验参数
        2.1 非空判断
        2.2 使用正则判断手机号码格式是否正确
    3.逻辑处理
        3.1 根据image_code_id编号提取redis数据库中，真实的图形验证码值real_image_code
        real_image_code有值：从redis数据库中删除（一个图形验证码只校验一次）
        real_image_code没有值：图形验证码过期了
        
        3.2 将用户填写的image_code和真实的图形验证码值进行比对
        #细节： 1.忽略大小写， 2.decode_responses=True,保持数据都是字符串类型
        
        3.3 不相等：提示前端图形验证码填写错误，前端：重新生成一张验证码图片
        
        TODO: 判断手机号码是否已经注册 【提高用户体验】
        
        3.4 相等：调用云通信工具类，发送短信验证码
        3.4.1 生成6位的随机短信
        3.4.2 调用CPP对象的send_template_sms发送短信验证码
        
        3.4.3 发送短信验证码失败：告知前端
        3.4.4 发送短信验证码成功：使用redis数据库保存正确的短信验证码值
        
    4.返回数据
        发送短信验证码成功 OK = 0
    """
    # 1.1 mobile: 手机号码，image_coed:用户填写的图形验证码值， image_code_id: UUID唯一编号
    param_dict = request.json
    mobile = param_dict.get("mobile")
    image_code = param_dict.get("image_code")
    image_code_id = param_dict.get("image_code_id")

    #  2.1 非空判断
    if not all([mobile, image_code, image_code_id]):
        # 参数不足
        current_app.logger.error("参数不足")
        # 返回错误信息
        err_dict = {"errno": RET.PARAMERR, "errmsg": "参数不足"}
        return jsonify(err_dict)

    #  2.2 使用正则判断手机号码格式是否正确
    if not re.match(r"1[3578][0-9]{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码格式错误")

    # 3.1 根据image_code_id编号提取redis数据库中，真实的图形验证码值real_image_code
    try:
        real_image_code = redis_store.get("Iamge_Code_%s" % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询redis图形验证码异常")

    # real_image_code有值：从redis数据库中删除（一个图形验证码只校验一次）
    if real_image_code:
        # 只是redis数据库删除了数据，变量中还有
        redis_store.delete("Iamge_Code_%s" % image_code_id)

    # real_image_code没有值：图形验证码过期了
    else:
        return jsonify(errno=RET.NODATA, errmsg="图形验证码过期了")

    # 3.2 将用户填写的image_code和真实的图形验证码值进行比对
    # 细节： 1.忽略大小写， 2.decode_responses=True,保持数据都是字符串类型
    if image_code.lower() != real_image_code.lower():
        # # 3.3 不相等：提示前端图形验证码填写错误，前端：获取4004错误状态码，重新生成一张验证码图片
        return jsonify(errno=RET.DATAERR, errmsg="图形验证码填写错误")

    # TODO: 判断手机号码是否已经注册 【提高用户体验】
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户数据异常")

    if user:
        # 当前手机号码已经注册
        return jsonify(errno=RET.DATAEXIST, errmsg="手机号码已经注册")

    # 3.4 相等：调用云通信工具类，发送短信验证码

    # 3.4.1 生成6位的随机短信
    real_sms_code = random.randint(0, 999999)
    # 不足6位，前面补零  000001
    real_sms_code = "%06d" % real_sms_code

    # 3.4.2 调用CPP对象的send_template_sms发送短信验证码
    # 参数1：发送到那个手机号码，参数2：发送短信的内容 参数3： 模板id
    try:
        result = CCP().send_template_sms(mobile, {real_sms_code, 5}, 1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="云通信发送短信验证码异常")

    # 3.4.3 发送短信验证码失败：告知前端
    if result == -1:
        return jsonify(errno=RET.THIRDERR, errmsg="云通信发送短信验证码异常")

    # 3.4.4 发送短信验证码成功：使用redis数据库保存正确的短信验证码值
    redis_store.setex("SMS_CODE_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, real_sms_code)

    # 4.发送短信验证码成功
    return jsonify(errno=RET.OK, errmsg="发送短信验证码成功")


# /passport/image_code?code_id=UUID编号
@passport_bp.route('/image_code')
def get_image_code():
    """生成验证码图片的后端接口"""

    """
    1.获取参数
        1.1 code_id: UUID唯一编码
    2.参数校验
        2.1 code_id非空判断
    3.业务逻辑
        3.1 调用工具类生成验证码图片，验证码真实值
        3.2 使用code_id作为key将验证码真实值存储到redis中，并且设置有效时长
    4.返回数据
        4.1 返回图片数据
    """

    # 1.1 code_id: UUID唯一编码
    code_id = request.args.get("code_id")

    # 2.1 code_id非空判断
    if not code_id:
        return abort(404)

    # 3.1 调用工具类生成验证码图片，验证码真实值
    image_name, real_image_code, image_data = captcha.generate_captcha()

    # 3.2 使用code_id作为key将验证码真实值存储到redis中，并且设置有效时长，方便下一个接口提取正确的值
    # Iamge_Code_UUID编号： 1234
    # 参数1：存储的key 参数2：有效时长， 参数3：存储的真实值
    redis_store.setex("Iamge_Code_%s" % code_id, constants.IMAGE_CODE_REDIS_EXPIRES ,real_image_code)

    # 4.1 直接返回图片数据，不能兼容所有浏览器

    # 构建响应对象
    response = make_response(image_data)
    # 设置响应头中返回的数据格式为：png格式
    response.headers["Content-Type"] = "png/image"

    return response


