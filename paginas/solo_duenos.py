from handles.selenium_handler import SeleniumHandler
from bs4 import BeautifulSoup
import requests
import time
import re
from handles.mongo import mongo

# TODO insert a bbdd (handle)
# implementar filtros (esto seria en modulo aparte)
# implementar alertas (modulo aparte)
# implementar crontab

class SoloDuenos:
    def __init__(self):
        self.filtro = ('casa', 'departamento', 'ph', 'alquiler')
        self.handler = SeleniumHandler()
        self.driver = self.handler.driver
        self.base_url = 'https://www.soloduenos.com/'
        self.session = requests.session()
        self.mongo = mongo()
        self.collection = self.mongo.get_collection('solo_duenos')
        self.main()

    def main(self):
        urls = [
            'https://www.soloduenos.com/BusquedaGeneral.asp?cmbZona=2', #(GBA)
            'https://www.soloduenos.com/BusquedaGeneral.asp?cmbZona=1'  #(CABA)
        ]        

        propiedades = []
        propiedades_out = []
        for url in urls:
            propiedades += self.get_propiedades(url)

        for propiedad in propiedades:
            data = self.get_data(propiedad)
            propiedades_out.append(data)
            if len(propiedades_out) == 20:
                self.mongo.insert_many(self.collection, propiedades_out)
                propiedades_out.clear()
        self.mongo.insert_many(self.collection, propiedades_out)

    def get_data(self, propiedad):
        # print(propiedad)
        response = self.session.get(propiedad)
        soup = BeautifulSoup(response.text, 'html.parser')
        precio_ubicacion = self.get_one(soup.find_all('div'),'alquiler')
        precio, ubicacion = self.parse_precio(precio_ubicacion) 
        direccion = self.get_one(soup.find_all('div'),'dirección')
        direccion = self.parse_direccion(direccion)
        data_inmueble = self.parse_data_inmueble(soup.find('div',{'name':'datos-ficha'}))
        
        # print(precio)
        # print(ubicacion)
        # print(direccion)
        # print(data_inmueble)
        # print()
        
        data_inmueble['link'] = propiedad,
        data_inmueble['precio'] = precio,
        data_inmueble['ubicacion'] = ubicacion,
        data_inmueble['direccion'] = direccion,
            
        return data_inmueble
    def get_one(self, soup, text):
        for item in soup:
            if text in item.text.lower():
                return item
    
    def parse_precio(self, data):
        divs = data.find_all('div')
        ubicacion_next = False
        ubicacion = None
        precio = None
        for div in divs:
            if 'direcc' in div.text.lower():
                break
            if precio and ubicacion:
                break
            if div.find_all('div') and len(div.find_all('div')) > 1:
                continue
            if ubicacion_next and not ubicacion:
                ubicacion = self.clean(div.text) 
                continue
            if not ubicacion_next and 'en:' in div.text.lower():
                ubicacion_next = True
                continue
            if ubicacion:
                precio = self.clean(div.text)
                precio = precio.split('$')[-1]
                if 's' in precio or 'venta' in precio.lower():
                    precio = None
                    continue
                precio = int(precio.replace('.','').replace(',',''))
            
        return precio, ubicacion
        
    def parse_direccion(self, data):
        divs = data.find_all('div')
        direccion_next = False
        direccion = None
        for div in divs:
            if div.find_all('div') and len(div.find_all('div')) > 1:
                continue
            if direccion_next:
                direccion = self.clean(div.text) 
                return direccion
            if 'dirección:' in div.text.lower():
                direccion_next = True 
        
        
    def parse_data_inmueble(self, data):
        data_out = {}
        rows = data.find_all('tr')
        notas = False
        for n, row in enumerate(rows):
            if n!= 0  and 'notas' in row.text.lower():
                notas = True
                continue
            if notas:
                data_notas = row.find('p')
                data_notas = self.clean(data_notas.text) if data_notas else None
                # continue
            if notas and data_notas:
                data_out['Notas'] = data_notas
                notas = False
                continue
            t_datas = row.find_all('td')
            key = None
            value = None
            for t_data in t_datas:
                if t_data.find_all('td') and len(t_data.find_all('td')) > 1:
                    continue
                if key:
                    value = self.clean(t_data.text)
                    if value == '' or value == None:
                        value = t_data.find('img')
                        if value and value.get('src') == 'Imagenes/oknuevo.gif':
                            value = True
                        else: 
                            value = False
                if t_data.text and t_data.text[-1] == ':' and not value:
                    key = self.clean(t_data.text)
                if key and value != None:
                    data_out[key] = value
                    key = None
                    value = None
        if 'Expensas' in data_out:
            expensas = data_out['Expensas']
            expensas = expensas.replace('.','').replace(',','')
            expensas = int(re.findall('\d+',expensas)[0])
            data_out['Expensas'] = expensas
        return data_out

    def clean(self, text):
        replace = ['\r','\n','\t']
        for rep in replace:
            text = text.replace(rep,'')
        text = text.strip().strip(':').strip()
        return text


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