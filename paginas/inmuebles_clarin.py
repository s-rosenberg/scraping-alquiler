from bs4 import BeautifulSoup
import requests
import json
from handles.mongo import mongo

class InmueblesClarin:
    def __init__(self, filtro):
        self.start_url = 'https://www.inmuebles.clarin.com/{tipo_propiedad}-{operacion}-region-{region}-{ambientes}-hasta-{max_precio}-pesos-pagina-{pagina}'
        self.filtros = self.parse_filtro(filtro)
        self.session = requests.session()
        self.base_url = 'https://www.inmuebles.clarin.com'
        self.api_url = 'https://api.sosiva451.com/Avisos/{id}'
        self.headers = self.get_headers()
        self.mongo = mongo()
        self.collection = self.mongo.get_collection('clarin')
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
                    id = link.split('-')[-1] if link else None
                    if id:
                        api_url = self.api_url.format(id=id)
                        api_response= self.session.get(api_url, headers=self.headers)
                        data_propiedad = api_response.json()
                        data_propiedad = self.get_propiedad(data_propiedad)
                        data_propiedad['url'] = link
                        propiedades.append(data_propiedad)
                        print(data_propiedad)
                pagina += 1
        self.mongo.insert_many(self.collection, propiedades)
    def get_propiedad(self, data):
        data_out = {
            'ubicacion': data.get('Barrio_t'),
            'ambientes': data.get('CantidadAmbientes_i'),
            'direccion': f'{data.get("Direccion_NombreCalle_t")} {data.get("Direccion_NumeroRedondeado_i")}',
            'exprensas': data.get("Expensas_i"),
            'fecha_aviso': data.get("FechaModificacionAviso_dt"),
            'precio': data.get("MontoOperacion_i"),
            'superficie_cubierta': data.get("SuperficieCubierta_d"),
            'superficie_total': data.get("SuperficieTotal_d"),
            'contacto': {'Fijo': data.get("TelefonoContacto_t"),
                        'Whatsapp': data.get("TelefonoWhatsApp_i")},
            'descripcion': self.clean(data.get("InformacionAdicional_t"))
        }
        return data_out     
    
    def get_headers(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.inmuebles.clarin.com/',
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
            filtro['region'] = region
            filtros_out.append(filtro)          
        
        return filtros_out      
    
    def clean(self, text):
        replace = ['\r','\n','\t']
        for rep in replace:
            text = text.replace(rep,'')
        text = text.strip().strip(':').strip()
        return text