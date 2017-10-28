from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
import platform
import time
import sys
import os

def main():
    import Authorization
    # with WebInterface(user=Authorization.GetUser(), password=Authorization.GetPassword()) as con:
    #     con.LogDiaper("dirty and wet")
    #     sess = Nursing(0,500,500)
    #     con.LogNursing(sess)
    from pprint import pprint
    baseTime = time.time()
    testNurse = Nursing(1, epoch=baseTime)
    testNurse.Switch(epoch=baseTime+120)
    pprint(testNurse.GetTimes(epoch=baseTime+120+220))
    diaper = Diaper("dirty and wet")
    print (diaper.type, ":", diaper.id)

class WebInterface(object):
    url = r"https://www.baby-connect.com/home"

    def __init__(self, user, password):
        self.user = user
        self.password = password

        if platform.system() == 'Linux':
            self.driver = webdriver.Firefox()
        else:
            self.driver = webdriver.Chrome()
        self.driver.get(self.url)
        elem = self.driver.find_element_by_name("email")
        elem.clear()
        elem.send_keys(user)
        elem = self.driver.find_element_by_name("pass")
        elem.send_keys(password)
        elem.send_keys(Keys.RETURN)
        timeCycles = 0
        timeWait = 2
        while "logout" not in self.driver.page_source:
            if timeCycles > 5:
                break
            time.sleep(timeWait)
            timeCycles += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__del__()
        
    def __del__(self):
        if self.driver is not None:
            self.driver.close()

    def LogDiaper(self, logType):
        diaper = None
        if isinstance(logType, Diaper):
            diaper = logType
        else:
            logType = str(logType)
            diaper = Diaper(logType)

        # Fire pop-up box for logging
        self.driver.find_element_by_partial_link_text("Diaper").click()
        time.sleep(1)

        # Set type of diaper and log it.
        self.driver.find_element_by_id(diaper.id).click()
        self.driver.find_element_by_css_selector(".ui-button-text-only .ui-button-text").click()
        # print ("Diaper logged...")

    def LogNursing(self, nursing):
        data = nursing.GetTimes()
        self.driver.find_element_by_partial_link_text("Nursing").click()
        time.sleep(1)
        elem = self.driver.find_element_by_id("timeinput")
        elem.clear()
        elem.send_keys(data['start'])
        elem = self.driver.find_element_by_id("endtimeinput")
        elem.clear()
        elem.send_keys(data['end'])
        duration = data['left'] + data['right']
        durM = 0
        durH = 0
        if duration > 60:
            durM = duration % 60
            durH = (duration-durM)/60
        else:
            durM = duration
        elem = self.driver.find_element_by_id("hduration")
        elem.clear()
        elem.send_keys(str(durH))
        elem = self.driver.find_element_by_id("mduration")
        elem.clear()
        elem.send_keys(str(durM))
        elem = self.driver.find_element_by_id("left_side")
        elem.clear()
        elem.send_keys(str(data['left']))
        elem = self.driver.find_element_by_id("right_side")
        elem.clear()
        elem.send_keys(str(data['right']))

        if data["last"] == 1:
            self.driver.find_element_by_id("last_left").click()
        else:
            self.driver.find_element_by_id("last_right").click()

        self.driver.find_element_by_css_selector(".ui-button-text-only .ui-button-text").click()
        print ("Nursing session logged...")

class Diaper(object):
    type=None
    id=None
    ids = { 
        "bm" : "diaper1", 
        "bmwet" : "diaper2",
        "wet" : "diaper3",
        "dry" : "diaper4"
    }
    def __init__(self, logType):
        self.logValue = logType
        dirtyOPts = 'poopy dirty messy poop crap'.split()
        wetOPts = 'wet pee'.split()

        isDirty = False
        isWet = False
        for opt in dirtyOPts:
            if opt in logType:
                isDirty = True
                break

        for opt in wetOPts:
            if opt in logType:
                isWet = True
                break

        if isDirty and isWet:
            self.type = "bmwet"
        elif isDirty and not isWet:
            self.type = "bm"
        else:
            self.type = "wet"

        # Sets the id code used on the BabyConnect website
        self.id = self.ids[self.type]

    def __repr__(self):
        return "Diaper: {} ({})".format(self.logValue, self.type)

    def get_type(self):
        return self.type

    def get_id(self):
        return self.id


# Class for handling the time tracking of a nursing session.
# This has the utilities to stop/start a session ans switch sides
class Nursing(object):
    def __init__(self, side, timeL=None, timeR=None, epoch=None, debug=None):
        self.timeStart = datetime.now() if epoch is None else datetime.fromtimestamp(epoch)
        if epoch is None:
            self.timeBegin = datetime.now() if timeL is None else datetime.now() - timedelta(seconds=(timeL+timeR))
        else:
            self.timeBegin = self.timeStart
        self.side = side  # 0 = L, 1 = R
        self.durL = 0 if timeL is None else timeL
        self.durR = 0 if timeR is None else timeR
        self.finishTime = self.timeStart
        self.done = False
        self.debug = debug
        self._debugMsg("Start:{}, Side:{}, Epoch:{}".format(self.timeStart, self.side, epoch))

    def __repr__(self):
        times = self.GetTimes()
        last = "right" if times["last"] else "left"
        outStr = "Nursing session:\n" + \
            "   Start       : {}\n".format(times["start"]) + \
            "   End Time    : {}\n".format(times["end"]) + \
            "   Time (Left) : {}\n".format(times["left"]) + \
            "   Time (Right): {}\n".format(times["right"]) + \
            "   Last Side   : {}\n".format(last)
        return str(outStr)

    def _GetNow(self, epoch=None):
        if epoch is None:
            return datetime.now()
        else:
            return datetime.fromtimestamp(epoch)

    def _debugMsg(self, msg):
        if self.debug is not None:
            print (msg)

    def Switch(self, epoch=None):
        self.AddTime(epoch)
        oldSide = self.side
        self.side = 0 if self.side else 1
        self._debugMsg("Switching sides: {}->{} --- epoch:{}".format(oldSide, self.side, epoch))

    def Pause(self, epoch=None):
        self.AddTime(epoch)
        self.timeStart = None
        self._debugMsg("Pause:{}".format(epoch))

    def Resume(self, epoch=None):
        self.timeStart = now = self._GetNow(epoch)
        self.done = False
        self._debugMsg("Resume:{}".format(epoch))

    def AddTime(self, epoch=None):
        now = self._GetNow(epoch)
        if self.timeStart is not None:
            length = (now - self.timeStart).total_seconds()
            if self.side:
                self.durR += length
                self._debugMsg("Adding {} seconds to right".format(length))
            else:
                self.durL += length
                self._debugMsg("Adding {} seconds to left".format(length))
        self.timeStart = now

    def Finish(self, epoch=None):
        self.AddTime(epoch)
        self.finishTime = self._GetNow(epoch)
        self.done = True
        self._debugMsg("Finishing: {}".format(self.finishTime))

    def GetTimes(self, epoch=None):
        now = None
        if not self.done:
            self.AddTime(epoch)
            now = self._GetNow(epoch)
        else:
            now = self.finishTime
        return {
            "start":self.timeBegin.strftime("%I:%M%p"), 
            "left":round((self.durL/60), 0), 
            "right":round((self.durR/60), 0),
            "end":now.strftime("%I:%M%p"),
            "last":self.side
        }

if __name__ == '__main__':
    main()