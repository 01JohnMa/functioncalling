from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
import hashlib
import base64
import hmac
from urllib.parse import urlencode
from urllib.parse import urlparse

'''
生成请求授权信息
parameter（request_url: 请求的 URL
method: HTTP 方法，"GET"、"POST" 
api_key: API 的密钥。
api_secret: API 的密钥对应的密钥）

return
构建最终的 URL，包括原始的请求 URL 和生成的授权信息，以参数形式拼接在 URL 中
'''
def assemble_auth_url(request_url, method, api_key, api_secret):
    u = urlparse(request_url)
    host = u.hostname
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    # print(date)
    # date = "Thu, 12 Dec 2019 01:57:27 GMT"
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
        api_key, "hmac-sha256", "host date request-line", signature_sha)
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }
    return request_url + "?" + urlencode(values)



# # 你的API密钥和密钥对应的密钥
# api_key = "your_api_key"
# api_secret = "your_api_secret"

# # 请求的URL和HTTP方法
# request_url = "https://api.example.com/resource"
# http_method = "GET"

# # 调用assemble_auth_url函数生成授权URL
# auth_url = assemble_auth_url(request_url, http_method, api_key, api_secret)

# # 打印生成的授权URL
# print(auth_url)