from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import time

class SeleniumHandler:
    def __init__(self):
        options = Options()
        options.headless = True
        self.driver = webdriver.Firefox(options=options)

    def __del__(self):
        self.driver.close()
        del self.driver
        
    def scroll_and_click(self, element):
        if type(element) == list:
            for el in element:
                ActionChains(self.driver).move_to_element(el).click().perform()
        else:
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
            ActionChains(self.driver).move_to_element(element).click().perform()

    def to_bs4(self):
        return BeautifulSoup(self.driver.page_source,'html.parser')
    
    def wait_until(self, xpath):
        retry = 0
        while retry < 10:
            try:
                element = self.driver.find_element_by_xpath(xpath)
                break
            except:
                retry += 1
                time.sleep(retry)
        