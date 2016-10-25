from datetime import datetime
from collections import OrderedDict
from hashlib import md5
import json
import time

from lxml import etree, html
import requests

IGP_EQ_URL = "http://www.igp.gob.pe/bdsismos/ultimosSismosSentidos.php"


def get_earthquakes_data(page=1):
    data = {
        'xjxfun': 'aux',
        'xjxr': int(time.time() * 1000),
        'xjxargs[]': ['N20', 'N%d' % page,
                      '<xjxobj>'
                      '<e><k>optionMonth0</k><v>S1</v></e>'
                      '<e><k>optionMonth1</k><v>S2</v></e>'
                      '<e><k>optionMonth2</k><v>S3</v></e>'
                      '<e><k>optionMonth3</k><v>S4</v></e>'
                      '<e><k>optionMonth4</k><v>S5</v></e>'
                      '<e><k>optionMonth5</k><v>S6</v></e>'
                      '<e><k>optionMonth6</k><v>S7</v></e>'
                      '<e><k>optionMonth7</k><v>S8</v></e>'
                      '<e><k>optionMonth8</k><v>S9</v></e>'
                      '<e><k>optionMonth9</k><v>S10</v></e>'
                      '<e><k>optionMonth10</k><v>S11</v></e>'
                      '<e><k>optionMonth11</k><v>S12</v></e>'
                      '</xjxobj>']
    }

    response = requests.post(IGP_EQ_URL, data=data)
    table_str = etree.fromstring(response.content)[0].text[1:]
    table = html.fragment_fromstring(table_str)
    header = [e.text for e in table[0]]

    earthquakes = []
    for row in table[1:]:
        earthquakes.append({header[i]: e.text for i, e in enumerate(row)})

    return earthquakes


def to_amigo_format(earthquake):
    datetime_str = '%s %s-0500' % (earthquake['Fecha Local'],
                                   earthquake['Hora Local'])
    datetime_iso = datetime.strptime(datetime_str,
                                     '%d/%m/%Y %H:%M:%S%z').isoformat()
    location = 'SRID=4326;POINT(%s %s)' % (earthquake['Longitud'],
                                           earthquake['Latitud'])
    amigo_data = {
        'datetime': datetime_iso,
        'intensity_locality': earthquake['Intensidad - Localidades'].strip(),
        'location': location,
        'magnitude_ml': float(earthquake['Magnitud'].split()[0]),
        'depth_km': int(earthquake['Profundidad'].split()[0])
    }
    json_data = json.dumps(OrderedDict(sorted(amigo_data.items(),
                                              key=lambda t: t[0])))
    amigo_id = md5(json_data.encode('utf8')).hexdigest()
    return amigo_id, amigo_data
