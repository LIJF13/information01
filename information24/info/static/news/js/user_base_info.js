function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(function () {

    $(".base_info").submit(function (e) {
        e.preventDefault()

        var signature = $("#signature").val();
        var nick_name = $("#nick_name").val();
        // var gender = $(".gender").val();
        var gender = $('input:radio[name="gender"]:checked').val();

        if (!nick_name) {
            alert('请输入昵称')
            return
        }
        if (!gender) {
            alert('请选择性别')
        }

        // 组织请求参数
        var params = {
            "signature": signature,
            "nick_name": nick_name,
            "gender": gender
        }

        // 发送请求修改资料
        $.ajax({
            url: "/user/user_base_info",
            type: "post",
            contentType: "application/json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            data: JSON.stringify(params),
            success: function (resp) {

                if (resp.errno == "0") {
                    // 更新父窗口内容
                    // 父html左侧昵称值
                    $('.user_center_name', parent.document).html(params['nick_name'])
                    // 修改父html右上角昵称值
                    $('#nick_name', parent.document).html(params['nick_name'])
                    $('.input_sub').blur()
                }else {
                    alert(resp.errmsg)
                }
            }
        })
    })
})