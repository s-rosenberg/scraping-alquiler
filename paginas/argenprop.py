from bs4 import BeautifulSoup
import requests
import json
import re
from handles.mongo import mongo

class ArgenProp:
    def __init__(self, filtro):
        self.start_url = 'https://www.argenprop.com/{tipo_propiedad}-{operacion}-{region}-{ambientes}-hasta-{max_precio}-pesos-pagina-{pagina}'
        self.filtros = self.parse_filtro(filtro)
        self.session = requests.session()
        self.base_url = 'https://www.argenprop.com'
        self.headers = self.get_headers()
        self.regex_section = re.compile(r'section_\d+')
        self.mongo = mongo()
        self.collection = self.mongo.get_collection('argenprop')

        self.main()
        
    def main(self):
        propiedades = []
        for filtro in self.filtros:
            
            pagina = 1
            while True:
                url = self.start_url.format(tipo_propiedad=filtro['tipo_propiedad'],
                                        operacion=filtro['operacion'],
                                        region=filtro['region'],
                                        ambientes=filtro['ambientes'],
                                        max_precio=filtro['max_precio'],
                                        pagina=pagina)
                response = self.session.get(url, headers=self.headers)
                data = BeautifulSoup(response.text,'html.parser')
                links_propiedades = data.find_all('a',{'class':'card'})
                links_propiedades = [self.base_url + link['href'] for link in links_propiedades if link.get('href')] if links_propiedades else None
                if not links_propiedades:
                    break
                for link in links_propiedades:
                    response = self.session.get(link, headers=self.headers)
                    data = BeautifulSoup(response.text,'html.parser')
                    data = self.get_propiedad(data)
                    print(data)
                    data['link'] = link
                    propiedades.append(data)
                    if len(propiedades) == 20:
                        self.mongo.insert_many(self.collection, propiedades)
                        propiedades.clear()
                pagina += 1
        if propiedades != []:
            self.mongo.insert_many(self.collection, propiedades)

    def get_propiedad(self, data):
        descripcion = data.find('div',{'class':'section-description--content'})
        descripcion = self.clean(descripcion.text) if descripcion else None
        direccion = data.find('h3',{'class':'titlebar__address'})
        # direccion = direccion.findNext('p') if direccion else None
        direccion = self.clean(direccion.text) if direccion else None
        precio = data.find('p',{'class':'titlebar__price'})
        precio = self.parse_precio(precio.text) if precio else None
        data = data.find_all('ul', {'id':self.regex_section})
        data = self.parse_data(data)
        data['Precio'] = precio
        data['Descripcion'] = descripcion
        data['Direccion'] = direccion
        # data_out = {
        #     'ubicacion': data.get('Barrio_t'),
        #     'ambientes': data.get('CantidadAmbientes_i'),
        #     'direccion': f'{data.get("Direccion_NombreCalle_t")} {data.get("Direccion_NumeroRedondeado_i")}',
        #     'exprensas': data.get("Expensas_i"),
        #     'fecha_aviso': data.get("FechaModificacionAviso_dt"),
        #     'precio': data.get("MontoOperacion_i"),
        #     'superficie_cubierta': data.get("SuperficieCubierta_d"),
        #     'superficie_total': data.get("SuperficieTotal_d"),
        #     'contacto': {'Fijo': data.get("TelefonoContacto_t"),
        #                 'Whatsapp': data.get("TelefonoWhatsApp_i")},
        #     'descripcion': self.clean(data.get("InformacionAdicional_t"))
        # }
        return data    
    
    def parse_data(self, data):
        data_out = {'Sueltos':[]}
        for section in data:
            items = section.find_all('li')
            for item in items:
                item = item.text
                if ':' in item:
                    key, value = item.split(':')
                    key = self.clean(key)
                    value = self.clean(value)
                    if key.lower() == 'expensas':
                        value = self.parse_precio(value)
                    data_out[key] = value
                else:
                    data_out['Sueltos'].append(self.clean(item))
    
        return data_out


    def parse_precio(self, precio):
        if 's' in precio or 'consultar' in precio.lower():
            return
        precio = self.clean(precio)
        precio = precio.strip().split(' ')[-1].replace(',','').replace('.','').strip()
        return precio

    def get_headers(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            # 'Referer': 'https://www.inmuebles.clarin.com/',
            'Connection': 'keep-alive',
        }
        return headers

    def parse_filtro(self, filtro):
        filtros_out = []
        with open(filtro) as file:
            data = json.load(file)
        
        regiones = data['region']
        del data['region']

        filtro = {}
        for key, val in data.items():
            if key == 'ambientes':
                val = [f'{n}-ambientes' for n in val]
            if type(val) == list:
                val = '-y-'.join(val)
            filtro[key] = val

        for region in regiones:
            filtro = filtro.copy()
            tipo_region = 'localidad' if region == 'capital-federal' else 'region'
            filtro['region'] = f'{tipo_region}-{region}'
            filtros_out.append(filtro)          
        
        return filtros_out      
    
    def clean(self, text):
        replace = ['\r','\n','\t']
        for rep in replace:
            text = text.replace(rep,'')
        text = text.strip().strip(':').strip()
        return text