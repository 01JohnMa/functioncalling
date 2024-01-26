import argparse
import asyncio
import json
import os
import re
import typing
import  yaml
import pandas as pd
import websockets
from rouge_chinese import Rouge
import jieba
import requests
# 业务侧转接后的接口地址
# ws://172.30.13.84:30002/websocket/aichat
# 接口参数
# {"type":1,"content":"曲柄销数目,每一曲柄的气缸数,相邻气缸的夹角","assist":"docqa"}
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 1000)
pd.set_option('display.width', 1000)

def read_config():
    """
    从 YAML 文件中读取配置信息。
    """
    config_file_path = "./config.yaml"

    if os.path.exists(config_file_path,):
        with open(config_file_path, 'r',encoding='utf-8') as config_file:
            config_data = yaml.safe_load(config_file)
        return config_data
    else:
        print("错误：找不到配置文件。")
        return {}

#从配置文件中获得url
config = read_config()
url = config.get("websocket_url", "")
print(url)
output_data_file = config.get("output_data_file", "./data/output_data/测试结果集.xlsx")
import json
import websockets

async def call_ws_api(data: str,  max_attempts: int = 5):
    """
    调用api生成召回结果，最多尝试max_attempts次
    """
    final_data = {}
    rec_data = {}
    
    attempt_count = 0
    
    while attempt_count < max_attempts:
        attempt_count += 1
        
        async with websockets.connect(url) as websocket:
            # 发送消息到服务器
            await websocket.send(data)
            
            # 接收服务器的响应
            is_continue = True
            
            while is_continue:
                try:
                    response = await websocket.recv()
                    res_data = json.loads(response)                    
                    # 获取状态信息
                    status = res_data['status']
                    target = res_data['target']
                    _type = res_data['type']
                    
                    if status == 0 and target == "add" and _type == 1:
                        print("问答开始")
                    elif status == 1 and target == "add" and _type == 1:
                        final_data = res_data
                    elif status == 1 and target == "update" and _type == 1:
                        final_data = res_data
                    elif status == 1 and target == "end" and _type == 1:
                        print("问答结束")
                        is_continue = False
                    elif status == 0 and target == "add" and _type == 2:
                        print("推荐相关问题")
                        rec_data = res_data
                        is_continue = False
                    else:
                        is_continue = False
                        break
                
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"WebSocket连接关闭：{e}")
                    return final_data, rec_data
                
                except Exception as e:
                    print(f"发生异常：{e}")
                    break
            
        # 如果成功收到响应，则跳出循环
        if final_data or rec_data:
            break
    print(f"final_data:{final_data}")
    print(f"rec_data:{rec_data}")
    return final_data, rec_data


def call_demo():
    """
    调用示例
    """
    data = {
        # "type": "1",
        # "content": "船级社入级规则有哪些？",
        # "assist": "docqa",                                              
        # "spaceIds": [88],
          "type": 1, "content":  "什么样的船舶可以不设置舱底排水装置?", "assist": "", "assistantId": "116", "spaceIds": [], "docIds": []
        # "docIds": [ 183 ]
    }

    # 运行异步任务
    final_data, rec_data = asyncio.get_event_loop().run_until_complete(call_ws_api(json.dumps(data)))
    # print("==" * 20)
    mes0 = final_data['messages'][0]
    ada0 = mes0['adaptiveCards'][0]
    paras = ada0['body']['source'][0]
    recall_list = [para.get('content', '') for para in paras[:5]]
    print(recall_list)
  


def get_ans_recall_sorted_res(final_data: typing.Dict):
    """
    从返回的结果中，获取召回排序的结果
    """
    print("in get_ans_recall_sorted_res")
    # print(final_data)
    try:
        mes0 = final_data['messages'][0]
        ada0 = mes0['adaptiveCards'][0]
        paras = ada0['body']['source'][0]
        return mes0['text'], paras['paragraph']
    except Exception as e:
        return "", ""


# 去除换行、空格，标点符号。
def remove_punctuation_and_whitespace(input_string):
    result_string = re.sub(r'[\W\s]', '', input_string)
    return result_string

'''
逐个输入问题获取召回结果判断正确片段是否在召回内容里返回一个字典
'''
def ask_and_save(question, target, correct_snippet, recall_max_num):
    ask_data = {
     
        "type": 1, "content":  question, "assist": "", "assistantId": "116", "spaceIds": [], "docIds": []
        
    }
    while True:
        try:
            answer, _ = asyncio.get_event_loop().run_until_complete(call_ws_api(json.dumps(ask_data)))
            print("-------------------")
            print('answer:', answer)
            break
        except Exception as e:
            print(e)
            continue
    # 获取召回的内容
    ans, paras = get_ans_recall_sorted_res(answer)

    recall_correct_index = 0
    correct_val = ''
    recall_list = [para.get('content', '') for para in paras[:recall_max_num]]
    print("===============================")
    print(ans)
    # 计算 Rouge 分数
    print("rouge -------------------")
    rouge = Rouge()
    #中文分词
    ans_ = ' '.join(jieba.cut(str(ans)))
    target_ = ' '.join(jieba.cut(str(target)))  
    try:
        rouge_scores = rouge.get_scores(target_,ans_) 
    except Exception as e:
        print(e)
        rouge_scores = rouge.get_scores('0','0') 
    print("============+++++++++++===================================")
    print(rouge_scores)
    print("============+++++++++++===================================")
    print("召回答案"+ans)
    print("标准答案："+str(target))
    print("============+++++++++++===================================")
    
    for index, val in enumerate(recall_list):
        if index == recall_max_num:
            break
        _val = remove_punctuation_and_whitespace(val)
        if isinstance(correct_snippet, str):
            correct_snippet = remove_punctuation_and_whitespace(correct_snippet)
        else:
            continue

        if correct_snippet in _val:
            recall_correct_index = index + 1
            correct_val = val
            break
    this_question_rel = {'question': question,
                         'target': target,
                         'answer': ans,
                         'rouge-1': rouge_scores[0]['rouge-1']['f'],
                         'rouge-2': rouge_scores[0]['rouge-2']['f'],
                         'rouge-l': rouge_scores[0]['rouge-l']['f']}
    for i in range(recall_max_num):
        this_question_rel['recall_' + str(i + 1)] = recall_list[i] if i < len(recall_list) else ''
    this_question_rel['recall_num'] = recall_correct_index
    this_question_rel['召回答案'] = correct_val
    this_question_rel['正确片段'] = correct_snippet
    
    return this_question_rel


def read_questions_then_call(filename: str, recall_max_num: int = 5, this_index: int = 0):
    """
    读取所有的问题集， 进行问答
    """
    xlsx = pd.ExcelFile(filename)
    dfs = {sheet: xlsx.parse(sheet) for sheet in xlsx.sheet_names}
    this_index = this_index  if this_index ==0 else this_index+1 
    for sheet_name, df in dfs.items():
        print(f'Sheet: {sheet_name}')
        try:
            if 'question' in df.columns and 'target' in df.columns :
                for index, row in df.loc[this_index:].iterrows():
                    # if index < 227:
                    #     continue
                    question = row['question']
                    target = row['target']
                    correct_snippet = row['正确片段']
                    print('###########')
                    print(index + 1, question, correct_snippet)
                    if isinstance(question, str) and len(question) > 5:
                        this_question_rel = ask_and_save(question, target, correct_snippet, recall_max_num)
                        print("ASK AND SAVE DONE ")
                        # if len(res_df) == 0:
                        #     res_df = pd.DataFrame(columns=this_question_rel.keys())
                        #每次问询得到的一行结果(列表类型)
                        res_ls = []
                        res_ls.append(this_question_rel)
                        df = pd.DataFrame(res_ls)
                        if not os.path.isfile(output_data_file):
                            df_read = pd.DataFrame()
                        else:
                            df_read = pd.read_excel(output_data_file)
                        # res_df = pd.concat([res_df, pd.DataFrame([this_question_rel])], axis=0,ignore_index=True)  
                        df = pd.concat([df_read, df], axis=0).reset_index(drop=True)
                        df.to_excel(output_data_file,index = False)
        except Exception as e:
                 print(f"Sheet {sheet_name} 处理出错：{e}")
                 print(f"列名: {df.columns.tolist()}")  # 转换成列表形式
                 print(f"Sheet 数据示例:\n{df.head()}")
                 continue  # 继续处理下一个 sheet
    # return res_df


def filter(filename):
    """
        将得到的结果，选出recall_num为0以及recall非0的写成两个表格。
    """
    df_read = pd.read_excel(filename)
    filtered_df_no_recall = df_read[df_read['recall_num'] == 0]
    filtered_df_recall = df_read[df_read['recall_num'] != 0]

    base_filename = "筛选结果"
    file_extention = "xlsx"
    counter1 = 1
    counter2 = 1
    no_recall_filename = f"{'no_recall'}_{base_filename}_{counter1}.{file_extention}"
    while os.path.isfile(no_recall_filename):
        counter1 += 1
        no_recall_filename = f"{'no_recall'}_{base_filename}_{counter1}.{file_extention}"
    filtered_df_no_recall.to_excel(no_recall_filename, index=False)

    recall_filename = f"{'recall'}_{base_filename}_{counter2}.{file_extention}"
    while os.path.isfile(recall_filename):
        counter2 += 1
        recall_filename = f"{'recall'}_{base_filename}_{counter2}.{file_extention}"
    filtered_df_recall.to_excel(recall_filename, index=False)

'''
解析命令行参数调用read_questions_then_call
'''
def main():
    parser = argparse.ArgumentParser(description="Read questions from an Excel file and perform Q&A.")
    parser.add_argument("filename", help="Path to the Excel file containing questions.")
    parser.add_argument("--recall_max_num", type=int, default=5, help="Maximum number of recalls to consider.")
    
    args = parser.parse_args()
    
    # 使用配置值
    # config = read_config()
    recall_max_num = args.recall_max_num
    input_data_file = args.filename
    output_data_max_index = 0
    if os.path.exists(output_data_file):
        df_in =pd.read_excel(input_data_file,sheet_name="20231124明细数据汇总")
        input_data_max_index = df_in.index.max()
        df_out = pd.read_excel(output_data_file)
        output_data_max_index = df_out.index.max()
        if input_data_max_index < output_data_max_index:
            print("当前输出文件索引大于输入索引，请判断输入文件")
        else:
           print("当前读取进度：{:.2%}".format( float(output_data_max_index) / float(input_data_max_index)))
    
    read_questions_then_call(input_data_file, recall_max_num, output_data_max_index)
    #df.to_excel(output_data_file, index=False)
    #filter(output_data_file)

if __name__ == '__main__':
    #  # 使用配置值
    # config = read_config()
    # url = config.get("websocket_url", "")
    # recall_max_num = config.get("recall_max_num", 5)
    # input_data_file = config.get("input_data_file","" )
    # output_data_file = config.get("output_data_file","")

    # if os.path.exists(output_data_file):
    #     os.remove(output_data_file)

    # df = read_questions_then_call(input_data_file , recall_max_num=5)
    # df.to_excel(output_data_file, index=False)
    # filter(output_data_file)
    print("任务开始")
    call_demo()
    #main()
    #python main.py "./data/input_data/20231124所有验证数据汇总-20231124-18点.xlsx" --recall_max_num 5
    print("任务结束")
