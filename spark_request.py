# -*- coding: utf-8 -*-
import threading
import time

import json
import websocket
from spark_auth_new import assemble_auth_url

import random
import string


def generate_uid():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


# wss连接地址（注意：这里需要将assembled_url替换成你自己生成的认证请求头）



# 建立ws短连接
ws = websocket.WebSocket()

def connect_gpt( content, history=None):
    if history is None:
        history = []
    wss_url = assemble_auth_url(request_url="wss://spark-api.xf-yun.com/v3.1/chat",
                        method='GET',
                        api_key='8fc84059dffbf29f12e6eef15d39fe2c',
                        api_secret='ZWZiYjc4MzgzZWNmZDRkZDZhNTdhNjBm')
    ws.connect(wss_url)
    new = {"role": "user", "content": content}
    # print(new)
    # print(history)
    history.append(new)
    # print(history)
    # 发送请求数据
    req = {
        "header": {
            "app_id": "5f5b57a1",
            "uid": generate_uid()
            # "app_id": "f060421a",
            # "uid": "8fc84059dffbf29f12e6eef15d39fe2c"
        },
        "parameter": {
            "chat": {
                "domain": "generalv3",

                # "domain": "industry",
                "temperature":0.5,
                # "top_k": 3,
                "max_tokens": 2048,
                "auditing": "default"
            }
        },
        "payload": {
            "message": {
                "text": history
            }
        }
    }
    data = json.dumps(req)
    # print("\n【发送信息:】")
    # print(content)
    ws.send(data)

    # 接收结果
    # print("\n【返回信息:】")
    recv = True
    re = ''
    while recv:
        data = ws.recv()
        # 解析结果的格式
        t = json.loads(data)
        print("===================1==========================")
        print(f"start**t:{t}***end")
        text = t["payload"]["choices"]["text"]
        cont = text[0]["content"]
        re += cont
        print(cont, end='')
        code = t["header"]["code"]
        status = t["header"]["status"]
        # 出错 或者 收到最后一个结果， 就要退出
        if code != 0 or status == 2:
            recv = False
    # print(re)
    # 关闭ws连接
    # print("\n【回答完毕】")
    ws.close()
    str2 = {"role": "assistant", "content": re}
    history.append(str2)
    print("=================2========================")
    print(f"history:{history}")
    print("=================3========================")
    print(f"re:{re}")
    #history是问答消息和回答内容，re是回答内容
    return history, re


ss = '''请你对标准答案和生成答案两者相关性进行判断并打分，
回答要求如下:
1、不要推理过程只给出分数
2、请按照1-100进行打分
标准答案：在船舶满载情况下,应考虑敞口货舱浸水至舱口边缘或舱口围板顶端的情况。生成答案：敞口集装箱船完整稳性计算时，应考虑货舱满载情况下的浸水情况。具体来说，假设敞口货舱浸水至舱口边缘或舱口围板的顶端（如货舱设有排水舷口，则假设浸水至其开口下缘）。同时，还应考虑货舱浸水的中间阶段。'''
history = []
connect_gpt(ss, history)
