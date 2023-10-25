import json 
import requests
import time
import urllib 
import logging
import signal
import sys

TOKEN = "6379449727:AAGdgVUyMe3CDjWhYx70O-7EiLRz9bJ6hq8"
OWM_KEY = "904d31598fd40a05a2eb0b95bd3fd2da"
POLLING_TIMEOUT = None


def getText(update):            return update["message"]["text"]
def getLocation(update):        return update["message"]["location"]
def getChatId(update):          return update["message"]["chat"]["id"]
def getUpId(update):            return int(update["update_id"])
def getResult(updates):         return updates["result"]

def getDesc(w):                 return w["weather"][0]["description"]
def getTemp(w):                 return w["main"]["temp"]
def getCity(w):                 return w["name"]
logger = logging.getLogger("weather-telegram")
logger.setLevel(logging.DEBUG)

cities = ["Hong Kong", "Kowloon"]
send_period = 60 * 60
def sigHandler(signal, frame):
    logger.info("SIGINT received. Exiting... Bye bye")
    sys.exit(0)

def configLogging():
    handler = logging.FileHandler("run.log", mode="w")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def parseConfig():
    global URL, URL_OWM, POLLING_TIMEOUT
    URL = "https://api.telegram.org/bot{}/".format(TOKEN)
    URL_OWM = "https://api.openweathermap.org/data/2.5/weather?appid={}&units=metric".format(OWM_KEY)
    POLLING_TIMEOUT

def makeRequest(url):
    logger.debug("URL: %s" % url)
    r = requests.get(url)
    resp = json.loads(r.content.decode("utf8"))
    return resp


def getUpdates(offset=None):
    url = URL + "getUpdates?timeout=%s" % POLLING_TIMEOUT
    logger.info("Getting updates") 
    if offset:
        url += "&offset={}".format(offset)
    js = makeRequest(url)
    return js

def buildKeyboard(items):
    keyboard = [[{"text":item}] for item in items]
    replyKeyboard = {"keyboard":keyboard, "one_time_keyboard": True}
    logger.debug(replyKeyboard)
    return json.dumps(replyKeyboard)

def buildCitiesKeyboard():
    keyboard = [[{"text": c}] for c in cities]
    keyboard.append([{"text": "Share location", "request_location": True}])
    replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
    logger.debug(replyKeyboard)
    return json.dumps(replyKeyboard)

def getWeather(place):
    if isinstance(place, dict): 
        lat, lon = place["latitude"], place["longitude"]
        url = URL_OWM + "&lat=%f&lon=%f&cnt=1" % (lat, lon)
        logger.info("Requesting weather: " + url)
        js = makeRequest(url)
        logger.debug(js)
        return u"%s \N{DEGREE SIGN}C, %s in %s" % (getTemp(js), getDesc(js), getCity(js))
    else:   
        url = URL_OWM + "&q={}".format(place)
        logger.info("Requesting weather: " + url)
        js = makeRequest(url)
        logger.debug(js)
        return u"%s \N{DEGREE SIGN}C, %s in %s" % (getTemp(js), getDesc(js), getCity(js))

def sendMessage(text, chatId, interface=None):
    text = text.encode('utf-8', 'strict')                                                       
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chatId)
    if interface:
        url += "&reply_markup={}".format(interface)
    requests.get(url)

def getLastUpdateId(updates):
    ids = []
    for update in getResult(updates):
        ids.append(getUpId(update))
    return max(ids)
    
chats = {}

def handleUpdates(updates):
    for update in getResult(updates):
        chatId = getChatId(update)
        try:
            text = getText(update)
        except Exception as e:
            logger.error("No text field in update. Try to get location")
            loc = getLocation(update)
            if (chatId in chats) and (chats[chatId] == "weatherReq"):
                logger.info("Weather requested for %s in chat id %d" % (str(loc), chatId))
                while True:
                    sendMessage(getWeather(loc), chatId)
                    time.sleep(send_period)
            continue
            
        if text == "/weather":
            keyboard = buildCitiesKeyboard()
            chats[chatId] = "weatherReq"
            sendMessage("Select a city", chatId, keyboard)
        elif text == "/start":
            sendMessage("Type /weather to get weather information", chatId)
        elif text.startswith("/"):
            logger.warning("Invalid command %s" % text)    
            continue
        elif (text in cities) and (chatId in chats) and (chats[chatId] == "weatherReq"):
            logger.info("Weather requested for %s" % text)
            while True:
                    sendMessage(getWeather(text), chatId)
                    time.sleep(send_period)
        else:
            keyboard = buildKeyboard(["/weather"])
            sendMessage("Type /weather to get weather information", chatId, keyboard)

def main():
    configLogging()
    parseConfig()
    signal.signal(signal.SIGINT, sigHandler) 
    last_update_id = None
    while True:
        updates = getUpdates(last_update_id)
        if len(getResult(updates)) > 0:
            last_update_id = getLastUpdateId(updates) + 1
            handleUpdates(updates)
        time.sleep(0.5)

if __name__ == "__main__":
    main()