import os
import sys
import json
import time
import ftfy
import asyncio
import aiohttp
import urllib.parse
from PIL import Image
from barcode import Code128
from selenium import webdriver
from barcode.writer import ImageWriter
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

if getattr(sys, 'frozen', False):
    __location__ = os.path.dirname(sys.executable)
else:
    __location__ = os.path.dirname(os.path.abspath(__file__))

options = {
    'font_size': 5,
    'text_distance': 3,
    'module_height': 7,
    'module_width': 0.2,
    'quiet_zone': 1,
    'font_path': os.path.join(__location__, 'arial.ttf')
}

with open(os.path.join(__location__,"cookies.txt")) as f:
    ck = json.loads(f.read())
with open(os.path.join(__location__,"headers.txt")) as f:
    head = json.loads(f.read())
with open(os.path.join(__location__,"body.txt")) as f:
    data = json.loads(ftfy.fix_encoding(f.read()))
with open(os.path.join(__location__,"loginData.txt")) as f:
    login = json.loads(f.read())  
    
class PostRequest:
    def __init__(self,header,cook,body,login):
        self.header = header
        self.cook = cook
        self.body = body
        self.login = login
        self.error = False
    async def updateCookies(self):
        options = Options()
        options.add_argument("-headless")
        driver = webdriver.Firefox(options=options)
        driver.get("https:/www.pochta.ru/api/auth/login")
        driver.find_element(By.ID, "username").send_keys(self.login['username'])
        driver.find_element(By.XPATH, "/html/body/div/div/div[1]/div/div[2]/div[1]/p/button").click()
        driver.find_element(By.ID, "userpassword").send_keys(self.login['userpassword'])
        time.sleep(0.5)
        driver.find_element(By.CLASS_NAME, "bnpUOZ").click()
        time.sleep(5)
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == 'session_state':
                self.cook["session_state"] = urllib.parse.unquote(cookie['value'])
            if cookie['name'] == 'POCHTA_CSRF':
                self.cook["POCHTA_CSRF"] = cookie['value']
            if cookie['name'] == 'POCHTASID':
                self.cook["POCHTASID"] = cookie['value']
            if cookie['name'] == 'session-cookie':
                self.cook["session-cookie"] = cookie['value']
        driver.quit()
        return self.cook
    async def make_request(self, session, attempt=0):
        if self.error == True:
            return None
        else:
            try:
                async with session.post(url="https://www.pochta.ru/api/pdf-form/api/v2/mail/register",headers=self.header,json=self.body,cookies=self.cook) as response:
                    if response.status == 200:
                        return await response.json()
                    elif attempt < 4:
                        print(f"> Попытка {attempt + 1} неудачна. Повтор...", end="\r")
                        return await self.make_request(session, attempt + 1)
                    else:
                        print(f"!! Ошибка: {response.status}")
                        self.error = True
                        return None
            except Exception as e:
                if attempt < 4:
                    print(f"!! Ошибка подключения: {e}. Повтор...")
                    return await self.make_request(session, attempt + 1)
                else:
                    print(f"!! Ошибка подключения после 5 попыток: {e}")
                    self.error = True
                    return None

    async def sendReq(self):
        amnt = int(input("==================================\nСколько кодов необходимо сделать?: "))
        stringRange = []
        connector = aiohttp.TCPConnector(limit=10)
        await self.updateCookies()
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.make_request(session) for _ in range(amnt)]
            results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            if result:
                try:
                    track_number = result["trackNumber"]
                    stringRange.append(track_number)
                    print(f"> {i + 1} Успех: {track_number}", end="\r")
                except KeyError:
                    print(f"! {i + 1} Ошибка обработки ответа: {result}")
            else:
                print(f"{i + 1} Не удалось получить данные.")
        print(f"==================================\n<< Создано кодов: {len(stringRange)} >>\n==================================")
        return stringRange
    
def scrapCodes(textElements):
    if len(textElements) == 0:
        return 0
    for i in range(len(textElements)):
        size = 198, 80
        myBar = Code128(textElements[i], writer=ImageWriter())
        myBar.save(os.path.join(__location__,"Tracks/") + "bar", options)
        myBar = Image.open(os.path.join(__location__,"Tracks/") + "bar.png")
        myBarRes = myBar.resize(size)
        myBarRes.save(os.path.join(__location__,"Tracks/") + "bar" + str(i+1) + ".png")
    os.remove(os.path.join(__location__,"Tracks/") + "bar.png")
              
scrapCodes(asyncio.run(PostRequest(head,ck,data,login).sendReq()))