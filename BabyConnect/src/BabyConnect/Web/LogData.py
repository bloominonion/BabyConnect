from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from datetime import datetime, timedelta
from pyvirtualdisplay import Display
from BabyConnect.LogTypes import Diaper, Nursing
from BabyConnect import YourSecrets
import socket
import platform
import time
import sys
import os

def main():
    print ("Test")
    with WebInterface(user=YourSecrets.BabyConnectLogin.user, 
                      password=YourSecrets.BabyConnectLogin.password) as con:
         con.LogDiaper("dirty and wet")
    #     sess = Nursing(0,500,500)
    #     con.LogNursing(sess)
    exit()
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
        self.driver = None

        socket.setdefaulttimeout(30)
        if platform.system() == 'Linux':
            # self.display = Display(visible=1, size=(1024, 768))
            # self.display.start()
            binary = FirefoxBinary('/usr/bin/firefox')
            caps = DesiredCapabilities().FIREFOX.copy()
            self.driver = webdriver.Firefox(timeout=30,
                                            capabilities=caps,
                                            executable_path='/usr/bin/geckodriver',
                                            firefox_binary=binary)
        else:
            self.driver = webdriver.Chrome()
        self.driver.set_page_load_timeout(30)
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
                print ("Failed to login to page")
                break
            time.sleep(timeWait)
            timeCycles += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__del__()

    def __del__(self):
        try:
            self.driver.close()
            self.driver.quit()
        except:
            pass

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
        try:
            self.driver.find_element_by_css_selector(".ui-button-text-only .ui-button-text").click()
            return True
        except:
            return False

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

        try:
            self.driver.find_element_by_css_selector(".ui-button-text-only .ui-button-text").click()
            return True
        except:
            return False


if __name__ == '__main__':
    main()
