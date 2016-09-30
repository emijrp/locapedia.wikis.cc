#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2016 emijrp <emijrp@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import re
import pywikibot
import time
import urllib
import urllib.request
import urllib.parse

"""
SELECT ?item ?itemLabel ?adm ?admLabel ?flag ?coatofarms ?map ?population ?area ?elevation ?coordinates ?border ?borderLabel ?osm ?commonscat
WHERE
{
	?item wdt:P31 wd:Q2074737 .
  
    OPTIONAL{?item wdt:P131 ?adm .} 
    OPTIONAL{?item wdt:P41 ?flag .} 
    OPTIONAL{?item wdt:P94 ?coatofarms .} 
    OPTIONAL{?item wdt:P242 ?map .} 
    OPTIONAL{?item wdt:P1082 ?population .} 
    OPTIONAL{?item wdt:P2046 ?area .}
    OPTIONAL{?item wdt:P2044 ?elevation .} 
    OPTIONAL{?item wdt:P625 ?coordinates .} 
    OPTIONAL{?item wdt:P47 ?border .} 
    OPTIONAL{?item wdt:P402 ?osm .} 
    OPTIONAL{?item wdt:P373 ?commonscat .} 

	SERVICE wikibase:label { bd:serviceParam wikibase:language "es" }
}
ORDER BY ?itemLabel
"""

def unquotefilename(filename):
    filename = urllib.parse.unquote(filename)
    if 'Special:FilePath' in filename:
        filename = filename.split('Special:FilePath/')[1]
    return filename

def main():
    site = pywikibot.Site('locapedia', 'wikiscc')
    minpoblacion = 1000
    prov2ccaa = {
        'Provincia de Albacete': 'Castilla-La Mancha', 
        'Provincia de Ávila': 'Castilla y León', 
        'Provincia de Badajoz': 'Extremadura', 
        'Provincia de Burgos': 'Castilla y León', 
        'Provincia de Cáceres': 'Extremadura', 
        'Provincia de Ciudad Real': 'Castilla-La Mancha', 
        'Provincia de Cuenca': 'Castilla-La Mancha', 
        'Provincia de Guadalajara': 'Castilla-La Mancha', 
        'Provincia de León': 'Castilla y León', 
        'Provincia de Palencia': 'Castilla y León', 
        'Provincia de Salamanca': 'Castilla y León', 
        'Provincia de Segovia': 'Castilla y León', 
        'Provincia de Soria': 'Castilla y León', 
        'Provincia de Toledo': 'Castilla-La Mancha', 
        'Provincia de Valladolid': 'Castilla y León', 
        'Provincia de Zamora': 'Castilla y León', 
    }
    ccaa2gitosm = {
        'Castilla-La Mancha': 'castilla-la-mancha',
        'Castilla y León': 'castilla-y-león',
        'Extremadura': 'extremadura',
    }
    
    prov2ccaa_list = [[k, v] for k, v in prov2ccaa.items()]
    prov2ccaa_list.sort()
    
    for prov, ccaa in prov2ccaa_list:
        with open('municipios-espana.json', 'r') as f:
            municipios = json.loads(f.read())
        
        municipios2 = {}
        for municipio in municipios:
            if not municipio['item'] in municipios2:
                municipios2[municipio['item']] = {}
            for k, v in municipio.items():
                if not k in municipios2[municipio['item']]:
                    if k in ['border', 'borderLabel']:
                        municipios2[municipio['item']][k] = [v]
                    else:
                        municipios2[municipio['item']][k] = v
                elif k == 'admLabel':
                    if 'provincia' in v.lower(): #overwrite, we prefer province
                        municipios2[municipio['item']][k] = v
                elif k in ['border', 'borderLabel']:
                    if not v in municipios2[municipio['item']][k]:
                        municipios2[municipio['item']][k].append(v)
                        municipios2[municipio['item']][k].sort()
        
        municipios2_list = [[v['itemLabel'], k, v] for k, v in municipios2.items()]
        municipios2_list.sort()
        for j, k, v in municipios2_list:
            if not 'admLabel' in v or ('admLabel' in v and v['admLabel'] != prov):
                continue
            time.sleep(0.1)
            
            nombre = 'itemLabel' in v and v['itemLabel'] or ''
            nombre_ = re.sub(' ', '-', nombre.lower())
            print('== %s ==' % (nombre))
            bandera = 'flag' in v and v['flag'] or ''
            bandera = unquotefilename(bandera)
            simbolo = 'coatofarms' in v and v['coatofarms'] or ''
            simbolo = unquotefilename(simbolo)
            mapa = 'map' in v and v['map'] or ''
            mapa = unquotefilename(mapa)
            provincia = v['admLabel']
            ccaa = prov2ccaa[provincia]
            poblacion = 'population' in v and v['population'] or ''
            superficie = 'area' in v and v['area'] or ''
            elevacion = 'elevation' in v and v['elevation'] or ''
            coordenadas = 'coordinates' in v and v['coordinates'] or ''
            if coordenadas:
                coordenadas = re.sub(r'(?i)(Point\(|\))', '', coordenadas)
                coordenadas = '%s, %s' % (coordenadas.split(' ')[1], coordenadas.split(' ')[0])
            limitrofecon = 'borderLabel' in v and (', '.join(v['borderLabel'])) or ''
            wikidata = 'item' in v and v['item'] or ''
            if wikidata:
                wikidata = wikidata.split('/entity/')[1]
            osm = 'osm' in v and v['osm'] or ''
            commonscat = 'commonscat' in v and v['commonscat'] or ''
            
            if poblacion and int(poblacion) >= minpoblacion:
                # calcular parametros desde ficheros OSM
                osmelementos = []
                urlpoly = 'raw.githubusercontent.com/JamesChevalier/cities/master/spain/%s/%s_%s.poly' % (ccaa2gitosm[ccaa], nombre_, ccaa2gitosm[ccaa])
                try:
                    print('https://%s' % (urlpoly))
                    req = urllib.request.Request('https://%s' % (urllib.parse.quote(urlpoly)), headers={ 'User-Agent': 'Mozilla/5.0' })
                    poly = urllib.request.urlopen(req).read().strip().decode('utf-8')
                    if os.path.exists('temp.poly'):
                        os.remove('temp.poly')
                    if os.path.exists('temp.osm'):
                        os.remove('temp.osm')
                    if 'polygon' in poly:
                        #print (poly)
                        with open('temp.poly', 'w') as g:
                            g.write(poly)
                        os.system('osmosis --read-pbf-fast spain-latest.osm.pbf file="spain-latest.osm.pbf" --bounding-polygon file="temp.poly" --write-xml file="temp.osm"')
                        #os.system('grep \'k="name"\' temp.osm | sort | uniq > temp2.txt')
                        with open('temp.osm', 'r') as g:
                            raw = g.read()
                            osmelementos = list(set(re.findall(r'<tag k="name" v="([^<>]+?)"/>', raw)))
                            osmelementos.sort()
                except:
                    pass
                
                osmelementos = ', '.join(osmelementos)
                output = """{{Portada
|nombre=%s
|nombre wiki=
|imagen cabecera=
|bandera=%s
|símbolo=%s
|mapa=%s
|provincia=%s
|comunidad autónoma=%s
|país=España
|habitantes=%s
|superficie=%s
|elevación=%s
|coordenadas=%s
|limítrofe con=%s
|conocido por=
|botones fondo=
|botones texto=
|commonscat=%s
|wikidata=%s
|osm=%s
|osm elementos=%s
}}""" % (nombre, bandera, simbolo, mapa, provincia, ccaa, poblacion, superficie, elevacion, coordenadas, limitrofecon, commonscat, wikidata, osm, osmelementos)
                print(output)
                
                #portadas = [nombre, 'Wiki %s' % (nombre), '%s Wiki' % (nombre)]
                portadas = [nombre]
                for portada in portadas:
                    print(portada)
                    if portada == nombre:
                        time.sleep(0.5)
                        page = pywikibot.Page(site, portada)
                        page.text = output
                        try:
                            page.save('BOT - Creando portada para [[%s]]' % (nombre), botflag=True)
                        except:
                            print('Error guardando la pagina. Reintentando en 10 segundos...')
                            time.sleep(10)
                            try:
                                page.save('BOT - Creando portada para [[%s]]' % (nombre), botflag=True)
                            except:
                                print('Error de nuevo. Saltamos')
                                pass
                    else:
                        red = pywikibot.Page(site, portada)
                        if not red.exists():
                            red.text = '{{:%s}}' % (nombre)
                            red.save('BOT - Creando portada para [[%s]]' % (nombre), botflag=True)
            else:
                print('No llega a %s habitantes, saltamos' % (minpoblacion))

if __name__ == '__main__':
    main()
