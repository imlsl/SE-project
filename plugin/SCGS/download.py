"""
-*- coding: utf-8 -*-
文件名:原创力文档下载.py
作者：zhaozhao
环境: PyCharm
功能：原创力文档下载(仅支持可免费预览的部分)
"""
import os
import re
import requests
import time
from PIL import Image
from tqdm import tqdm

def get_html(url):
    html = requests.get(url)
    html.encoding = 'utf-8'
    return html.text

def get_params(url):
    html = get_html(url)
    aid = re.findall(pattern='aid: (.*?),', string=html, flags=re.S)[1]
    pages = re.findall(pattern='preview_page: (.*?),', string=html, flags=re.S)[0]
    view_token = re.findall(pattern="view_token: '(.*?)' //预览的token", string=html, flags=re.S)[0]
    params = []
    for page in range(1, int(pages) + 1, 6):
        param = {
            'project_id': '1',
            'aid': aid,
            'view_token': view_token,
            'page': page}
        params.append(param)
    return params

def img_to_pdf(folder_path, pdf_file_path):
    files = os.listdir(folder_path)
    png_files = []
    sources = []
    for file in files:
        if "png" in file or "jpg" in file:
            png_files.append(folder_path + file)
    try:
        png_files.sort(key=lambda x: int(str(re.findall("\d+", x)[0])))
    except IndexError:
        files.sort()
    output = Image.open(png_files[0])
    png_files.pop(0)
    for file in png_files:
        png_file = Image.open(file)
        sources.append(png_file)
    output.save(pdf_file_path, "pdf", save_all=True, append_images=sources)

def main():
    url = input("请输入文档链接：")
    path = input("请输入保存路径：")
    title = re.findall(pattern="title: '(.*?)', //文档标题", string=get_html(url), flags=re.S)[0]
    img_path = path +'\\'+ title.split('.')[0]
    for param in tqdm(get_params(url), desc="下载进度", unit="epoch", colour='green', ncols=100):
        headers = {'Accept': '*/*',
                   'Accept-Encoding': 'gzip, deflate, br',
                   'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                   'Connection': 'keep-alive',
                   'DNT': '1',
                   'Host': 'openapi.book118.com',
                   'Referer': 'https://max.book118.com/',
                   'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Microsoft Edge";v="104"',
                   'sec-ch-ua-platform': '"Windows"',
                   'Sec-Fetch-Dest': 'script',
                   'Sec-Fetch-Mode': 'no-cors',
                   'Sec-Fetch-Site': 'same-site',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.81 Safari/537.36 Edg/104.0.1293.54'}
        html = requests.get(url='https://openapi.book118.com/getPreview.html', headers=headers, params=param)
        html.encoding = 'utf-8'
        res = re.findall(pattern=r'"data":(.*?),"pages"', string=html.text, flags=re.S)[0]
        res = eval(res.replace('\\', ''))  # 将字符串转换为字典
        for k, v in res.items():
            img = requests.get('https:' + v).content
            if not os.path.exists(img_path):
                os.mkdir(img_path)
            with open(img_path+'\\'+k +'.png', 'wb') as f:
                f.write(img)
            # print("第 {} 页下载成功".format(k))
        time.sleep(3)
    img_to_pdf(img_path+'\\', img_path+'\\'+title.split('.')[0]+'.pdf')
    print("文档下载成功！")

if __name__ == '__main__':
    main()
