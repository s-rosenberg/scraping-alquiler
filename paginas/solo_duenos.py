from handles.selenium_handler import SeleniumHandler
from bs4 import BeautifulSoup
import requests
import time
import re

class SoloDuenos:
    def __init__(self):
        self.filtro = ('casa', 'departamento', 'ph', 'alquiler')
        self.handler = SeleniumHandler()
        self.driver = self.handler.driver
        self.base_url = 'https://www.soloduenos.com/'
        self.session = requests.session()
        self.main()

    def main(self):
        urls = [
            'https://www.soloduenos.com/BusquedaGeneral.asp?cmbZona=2', #(GBA)
            'https://www.soloduenos.com/BusquedaGeneral.asp?cmbZona=1'  #(CABA)
        ]        

        propiedades = []
        for url in urls:
            propiedades += self.get_propiedades(url)

        for propiedad in propiedades:
            self.get_data(propiedad)

    def get_date(self, propiedad):
        response = self.session.get(propiedad)
        soup = BeautifulSoup(response.text, 'html.parser')
        
    def get_propiedades(self, url):
        self.driver.get(url)
        checkboxs = self.driver.find_elements_by_xpath("//input[@type='checkbox']")
        checkboxs = [c.find_element_by_xpath('..') for c in checkboxs]
        
        clickear = []
        for checkbox in checkboxs:
            if checkbox.text.lower().strip() in self.filtro:
                clickear.append(checkbox)
        
        clickear = [c.find_element_by_xpath(".//input") for c in clickear]
        
        self.handler.scroll_and_click(clickear)
        
        submit = self.driver.find_element_by_xpath("//input[@type='submit']")
        self.handler.scroll_and_click(submit)
        time.sleep(5)
        self.handler.wait_until("//input[@type='submit']")
        
        submit = self.driver.find_element_by_xpath("//input[@type='submit']")
        self.handler.scroll_and_click(submit)
        time.sleep(5)
        
        # recorro las paginas y traigo las propiedades
        propiedades = []
        first = True
        while True:
            self.handler.wait_until("//font[@class='menubarrasuperiorB']")
            soup = self.handler.to_bs4()
            links = soup.find_all('a',{'target':'_self'})
            if links == []:
                break
            links = {self.base_url + link['href'] for link in links if link.get('href')}
            propiedades += list(links)
            if first:
                next_url = self.get_next_url(soup)
                first = False
            else:
                url = self.driver.current_url
                next_url = self.change_url(url)
            self.driver.get(next_url)
        return propiedades
    def get_next_url(self, soup):
        urls = soup.find_all('a')
        url = [url['href'] for url in urls if 'whichpage' in url['href']]
        return self.base_url[:-1] + self.change_url(url[0]) if url != [] else None

    def change_url(self, url):
        whichpage = re.compile(r'whichpage=\d+') 
        num = whichpage.search(url)
        if num:
            num = int(re.findall('\d+', num.group())[0])
            num += 1
            url = re.sub(whichpage,f'whichpage={num}', url)
            return url