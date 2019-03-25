import qiniu

# 验证身份用到的key
access_key = "W0oGRaBkAhrcppAbz6Nc8-q5EcXfL5vLRashY4SI"
secret_key = "tsYCBckepW4CqW0uHb9RdfDMXRDOTEpYecJAMItL"
# 存储空间名字
bucket_name = "information24"


# 上传图片数据到七牛云平台（工具）
def upload_image(data):

    # data:图片的二进制数据
    if not data:
        raise AttributeError("图片数据为空")

    # 七牛云进行权限校验
    q = qiniu.Auth(access_key, secret_key)
    # 上传图片的名称，如果不指明，七牛云会默认分配一个唯一的图片名称
    # key = 'hello'

    # 读取空间名称
    token = q.upload_token(bucket_name)

    try:
        # 调用sdk中的方法将图片上传到七牛云
        ret, info = qiniu.put_data(token, None, data)
    except Exception as e:
        raise e

    print(ret)
    print("---------")
    print(info)

    if ret is not None:
        print('All is OK')
    else:
        print(info)  # error message in info

    if info.status_code != 200:
        raise AttributeError("上传图片到七牛云异常")

    # 返回图片名称
    return ret.get("key")


if __name__ == '__main__':

    # 读取图片二进制数据
    file = input("输入图片的地址:")
    with open(file, "rb") as f:
        upload_image(f.read())