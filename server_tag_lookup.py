from lxml import html
import requests
import time
from google.appengine.api import urlfetch
import models
import logging

__author__ = 'mwoods'


# TODO: Look into using the threading module
# http://stackoverflow.com/questions/2632520/what-is-the-fastest-way-to-send-100-000-http-requests-in-python

#TODO: use google app enginess asynchronous libraries
#https://cloud.google.com/appengine/docs/python/urlfetch/asynchronousrequests

def time_to_connect_logger(ttc):
    """function to log response time for url connections
        ttc = time_to_connect
    """
    if ttc < 10:
        logger = logging.info
    elif ttc < 30:
        logger = logging.warning
    else:
        logger = logging.error
    logger('Time to Connect: %.2f secs' % ttc)


def get_dom(url):
    #print 'starting connection',  url
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux i686)\
                               AppleWebKit/537.36 (KHTML, like Gecko)\
                               Chrome/39.0.2171.95\
                               Safari/537.36"}
    start = time.time()
    urlfetch.set_default_fetch_deadline(60)
    resp = requests.get(url, headers = headers)
    if resp.status_code == 200:
        dom = html.fromstring(resp.text)
        time_to_connect_logger(time.time() - start)
        return dom
    else:
        raise ValueError('Status Code is %s for url %s'%(str(resp.status_code), url))

def get_text(el):
    return el.text_content().strip()

class DellDomChange(Exception):
    pass


class DellLookUp(object):
    def __init__(self, tag):
        self.tag = tag
        self.dom = get_dom(self.url)
        self._mem_header_data = {}
        self._mem_detail_data = []

    @property
    def url(self):
        url_template = "http://www.dell.com/support/home/us/en/19/product-support/servicetag/%s/configuration"
        return url_template % self.tag

    @property
    def header_data(self):
        if self._mem_header_data == {}:
            ssa = self.dom.xpath("//div[@id='subSectionA']/div/div/div/table")
            if not ssa:
                logging.error("Table in SubsectionA not found")
                return {}

            cells = ssa[0].findall('.//td')
            if not cells:
                logging.error("No Cells Found from SubSectionA")
            for i in range(0, len(cells), 2):
                #runs through list in chunks of 2
                label, value = cells[i : (i+2)]
                label, value = label.text.strip(), value.text.strip()
                self._mem_header_data[label] = value
                if label == 'Computer Model':
                    self._mem_header_data['product_number'] = value
        return self._mem_header_data

    @property
    def detail_data(self):

        if self._mem_detail_data == []:
            _schema = ['Part Number', 'Quantity', 'Description']

            ssb = self.dom.xpath("//div[@id='subSectionB']")
            if not ssb:
                return []

            title_row = [cell.text.strip() for cell in ssb[0].findall('.//td/div/b')]

            if len(ssb) <> 1:
                raise DellDomChange("not exactly 1 div tag with subSectionB using server tag %s" % self.tag)

            if title_row[:3] != _schema:
                raise DellDomChange("structure of table in subSectionB has changed using server tag %s" % self.tag)

            els = ssb[0].findall('.//td/div')
            for i in range(0, len(els), 3):
                part_number, qty, description = els[i:(i + 3)]
                if part_number.text.strip() == '':
                    continue
                else:
                    self._mem_detail_data.append({'part_number': part_number.text.strip(),
                                        'qty': qty.text.strip(),
                                        'description': description.text.strip()
                                        })
        return self._mem_detail_data


class HPLookUp(object):
    def __init__(self, tag):
        self.tag = tag
        self.dom = get_dom(self.url)
        self._mem_header_data = {}
        self._mem_detail_data = []

    @property
    def url(self):
        url_template = "http://partsurfer.hpe.com/Search.aspx?searchText=%s"
        return url_template % self.tag

    @property
    def header_data(self):
        if self._mem_header_data == {}:
            #serial_number = self.dom.xpath("//span[@id='ctl00_BodyContentPlaceHolder_lblSerialNumber']")
            #self.header_data.append({'serial_number': serial_number[0].text.strip()})
            product_number = self.dom.xpath("//span[@id='ctl00_BodyContentPlaceHolder_lblProductNumber']")
            if product_number:
                self._mem_header_data['product_number'] = product_number[0].text.strip()
        return self._mem_header_data

    @property
    def detail_data(self):
        if self._mem_detail_data == []:
            combom_table = self.dom.xpath("//table[@id='ctl00_BodyContentPlaceHolder_gridCOMBOM']")
            if not combom_table:
                return []
            rows = combom_table[0].getchildren()
            for row in rows[1:]:
                part_no, desc, qty = row.getchildren()
                self._mem_detail_data.append({'part_number': get_text(part_no),
                                         'description': get_text(desc),
                                         'qty': get_text(qty)
                                         })
        return self._mem_detail_data




class ServerTagLookUp:

    def __init__(self, tags, manf):
        assert manf in ['hp', 'dell'], 'Unknown Manufacturer'
        scrapers = {'hp': HPLookUp, 'dell': DellLookUp}

        self.tags = tags
        self.manf = manf
        self.scraper = scrapers[manf]
        self.results = []

        #start the scraping jobs
        self._scrape()

    def enrich_components(self, component_list):
        #TODO: probably should refactor into main.py
        start = time.time()
        for comp in component_list:
            product = comp.get('part_number', '')
            description = comp.get('description', '')
            internal_comp, cat_sub_type = None, None
            part = models.OEMCompDBAPI(self.manf, product, description)
            #comp_detail = part.get_component()
            #if comp_detail is None:
            #    comp_detail = part.set_component(description)
            #internal_sku, component_class = comp_detail.internal_sku, comp_detail.component_class
            internal_sku, component_class, source = part.product_detail
            comp['internal_component'] = internal_sku
            comp['cat_sub_type'] = component_class
            comp['is_included'] = part.is_included
        logging.info('elapsed time to enrich components: ' +  str(time.time() - start))
        return component_list

    def _scrape(self):
        for tag in self.tags:
            model = self.scraper(tag)
            self.results.append({'tag': tag,
                                'components': self.enrich_components(model.detail_data),
                                'product_number' : model.header_data.get('product_number', None)}
                                )





def test1():
    import time

    dell_tags = ['DGDHXP1',
                '9DKYWQ1',
                '978SRR1',
                'HHXC0L1',
                '7Z4Z6S1',
                'F68DBG1',
                '82P02C1']
    hp_tags_good = ['MXQ03402B7', 'SGH038X5AR']
    hp_tags_bad = ['2UX7380244', '2UX7380243']
    start = time.time()
    tag = hp_tags_good[0]

    start = time.time()
    print ServerTagLookUp(hp_tags_bad, 'hp')
    print ServerTagLookUp([dell_tags[0]], 'dell')
    #print S.results
    print time.time() - start

if __name__ == "__main__":
    test1()


"""
DGDHXP1
9DKYWQ1
978SRR1
HHXC0L1
7Z4Z6S1
F68DBG1
82P02C1
MXQ03402B7
SGH038X5AR
"""

