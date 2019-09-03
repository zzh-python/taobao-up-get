# -*- coding: utf-8 -*-
import scrapy
# 加载requests库
import requests
# 加载正则表达式模块
import re
import time,random
from scrapy_redis.spiders import RedisSpider
#重写
from scrapy.http import Request
#获取cookie相关模块
import asyncio
from pyppeteer import launch
from retry import retry      # 设置重试次数用的


# class ExampleSpider(scrapy.Spider):
class ExampleSpider(RedisSpider):

    name = 'example'
    allowed_domains = ['taobao.com']
    # start_urls = ['https://s.taobao.com/search?q=' + '袜子']
    #start_urls 更换成redis_key
    redis_key = 'tabaoredis:start-urls'  #名字随意，要记住

    def __init__(self):
        self.cookielist='' #未处理过的cookie
        self.cookie = self.get_cookie_dic('wangzhewudi0806', 'xf950628')  # 要改传入参数账号密码#处理过的cookies
        self.headers={
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
        }
        # print('zzhcookie:'+self.cookie)

    def get_cookie_dic(self,username,password):

        async def main(username, password, url):  # 主函数
            browser = await launch({'headless': False, 'args': ["--disable-infobars"]})  # headless设置无界面模式
            page = await browser.newPage()
            await page.goto(url)
            print('注入js')
            # 以下为插入中间js，将淘宝会为了检测浏览器而调用的js修改其结果。
            await page.evaluate(
                '''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => undefined } }) }''')

            try:
                await page.click('a.forget-pwd.J_Quick2Static')
                print('切换到密码登录页面')
                cookie = await login(page, username, password)
                return cookie
            except Exception as e:
                print('直接进入密码登录页面', e)
                cookie = await login(page, username, password)
                return cookie

        async def login(page, username, password):  # 登录动作
            time.sleep(1)
            print('输入账号和密码')
            await page.type('input#TPL_username_1', username)
            time.sleep(1)
            await page.type('input#TPL_password_1', password)
            time.sleep(1)

            ##############################
            # 检测页面是否有滑块。原理是检测页面元素。
            slider = await page.Jeval('#nocaptcha', 'node => node.style')  # 是否有滑块
            if slider:
                print('当前页面出现滑块')
                # await page.screenshot({'path': './headless-login-slide.png'}) # 截图测试
                flag, page = await mouse_slide(page=page)  # js拉动滑块过去。
                # if flag:
                #     await page.keyboard.press('Enter')  # 确保内容输入完毕，少数页面会自动完成按钮点击
                #     print("print enter", flag)
                #     await page.evaluate('''document.getElementById("J_SubmitStatic").click()''')  # 如果无法通过回车键完成点击，就调用js模拟点击登录按钮。
                #
                #     time.sleep(2)
                #     # cookies_list = await page.cookies()
                #     # print(cookies_list)
                #     await get_cookie(page)  # 导出cookie 完成登陆后就可以拿着cookie玩各种各样的事情了。

            #################
            # 点击登录按钮
            await page.click('button#J_SubmitStatic')
            time.sleep(2)
            print('点击登录')
            # 在while循环里强行查询某元素进行等待
            # while not await page.waitForXPath('//li[@id="J_SiteNavLogin"]'):
            #     return None
            print('登录成功！')

            ck = await get_cookie(page)
            # await save_cookie(ck)
            return ck

        ##后加
        #
        # def retry_if_result_none(result):
        #     return result is None
        #
        # @retry(retry_on_result=retry_if_result_none, )
        async def mouse_slide(page=None):
            await asyncio.sleep(2)
            try:
                # 鼠标移动到滑块，按下，滑动到头（然后延时处理），松开按键
                await page.hover('#nc_1_n1z')  # 不同场景的验证码模块能名字不同。
                await page.mouse.down()
                await page.mouse.move(2000, 0, {'delay': random.randint(1000, 2000)})
                await page.mouse.up()
            except Exception as e:
                print(e, ':验证失败')
                return None, page
            else:
                await asyncio.sleep(2)
                # 判断是否通过
                slider_again = await page.Jeval('.nc-lang-cnt', 'node => node.textContent')
                if slider_again != '验证通过':
                    return None, page
                else:
                    # await page.screenshot({'path': './headless-slide-result.png'}) # 截图测试
                    print('验证通过')
                    return 1, page

        #################

        async def get_cookie(page):  # 获取登录后cookie
            # https: // cart.taobao.com / cart.htm?spm = a21bo.2017.1997525049.1.5af911d9PDSG8a &from=mini & pm_id = 1501036000a02c5c3739
            cookies_list = await page.cookies('https://cart.taobao.com')
            self.cookielist=cookies_list
            print('cookielist')
            print(cookies_list)
            cookies = ''
            for cookie in cookies_list:
                str_cookie = '{0}={1};'
                str_cookie = str_cookie.format(cookie.get('name'), cookie.get('value'))
                cookies += str_cookie
            # print(cookies)
            return cookies

        async def save_cookie(cookies):  # 保存到本地
            with open(r'./cookies.txt', 'w', encoding='utf-8') as f:
                f.write(cookies)
                print('保存成功')

        @retry(tries=1)
        def run():
            # global count
            count=1
            print('第%s次尝试请求' % count)
            url = 'https://login.taobao.com/member/login.jhtml?redirectURL=https://www.taobao.com/'
            # 协程，开启个无限循环的程序流程，把一些函数注册到事件循环上。当满足事件发生的时候，调用相应的协程函数。
            loop = asyncio.get_event_loop()
            m = main(username, password, url)
            ck = loop.run_until_complete(m)  # 将协程注册到事件循环，并启动事件循环
            count += 1
            return ck

        ck = run()
        if ck is not None:
            return ck

# 重写start_requests 是scrapy 的，这个是scrapy-redis的
#  RedisSpider.make_requests_from_url()
    def make_requests_from_url(self, url):
        # print('zzh你重写的函数被调用了哦')
        if self.cookie is not None:
             return Request(url,
                            # headers=self.headers,
                            cookies=self.cookielist,
                            encoding='UTF-8',
                            dont_filter=True
                            #,meta={} #自定义...
                       )


    def parse(self, response):
        information_list = []
        print(response.text)
        try:
            find_price = re.findall(r'\"view_price\"\:\"[\d\.]*\"', response.text)
            find_title = re.findall(r'\"raw_title\"\:\".*?\"', response.text)
            for i in range(len(find_price)):
                price = eval(find_price[i].split(':')[1])
                title = eval(find_title[i].split(':')[1])
                information_list.append([price, title])
        except RuntimeError:  # 一般超时错误
            print('htmlError???')

        headline = "{:4}\t{:8}\t{:16}"
        print(headline.format("序号", "价格", "商品名称"))
        num = 0
        for i in information_list:
            num = num + 1
            print(headline.format(num, i[0], i[1]))