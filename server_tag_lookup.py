from lxml import html
#import requests
#import requests_toolbelt.adapters.appengine
#requests_toolbelt.adapters.appengine.monkeypatch()
import time
from google.appengine.api import urlfetch
import models
import logging
import urlparse

__author__ = 'mwoods'

#TODO: Need to create a version that uses either requests or urllib2 to handle off line use

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

class STLResponse:
    url = None
    text = None
    status_code = None


def get_resp(url):

    parsed_uri = urlparse.urlparse(url)

    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux i686)\
                               AppleWebKit/537.36 (KHTML, like Gecko)\
                               Chrome/39.0.2171.95\
                               Safari/537.36"}

    urlfetch.set_default_fetch_deadline(60)
    resp = urlfetch.fetch(url, headers = headers, validate_certificate = (parsed_uri.scheme == "https"))

    if resp.status_code == 200:
        tmp = STLResponse()
        tmp.text = resp.content
        tmp.url = urlparse.urljoin(url, resp.final_url) if resp.final_url else url
        tmp.status_code = resp.status_code
        return tmp
    else:
        raise ValueError('Status Code is %s for url %s'%(str(resp.status_code), url))



def get_text(el):
    return el.text_content().strip()

class DellDomChange(Exception):
    pass

class DellTagNotFound(Exception):
    pass

class IBMDomChange(Exception):
    pass

class DellLookUp(object):
    def __init__(self, tag):
        self.tag = tag
        self.resp = get_resp(self.url)
        self.dom = html.fromstring(self.resp.text)
        self._mem_header_data = {}
        self._mem_detail_data = []

        if self.resp.url != self.url:
            logging.critical("Dell Request was redirected: to %s"%self.resp.url)

    @property
    def url(self):
        url_template = "http://www.dell.com/support/home/us/en/19/product-support/servicetag/%s/configuration?s=BSD"
        return url_template % self.tag

    @property
    def header_data(self):
        #added
        if 'IsInvalidSelection=True' in self.resp.url:
            raise DellTagNotFound("Redirected to 'Invalid Selection URL'")


        if self._mem_header_data == {}:
            ssa = self.dom.xpath("//div[@id='subSectionA']/div/div/div/table")
            if not ssa:
                err_msg = "Dell Header Table in not found for tag %s"%self.tag
                logging.critical(err_msg)
                raise DellDomChange(err_msg)
                #return {}

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
            #print self.tag, "||||", self.header_data
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
        self.resp = get_resp(self.url)
        self.dom = html.fromstring(self.resp.text)
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


class IBMLookUp(object):
    #FOR TESTING  ?manf=ibm&server_tag=7944|KQ095DA
    def __init__(self, tag):
        self.type, self.serial = tag.split('|')
        self.resp = get_resp(self.url)
        self.dom = html.fromstring(self.resp.text)
        self._mem_header_data = {}
        self._mem_detail_data = []
        self.ibm_sys_tables = self.dom.find_class("ibm-data-table")
        self.INDEX_FOR_HEADER_DATA = 0
        self.INDEX_FOR_PRODUCT_DATA = 2


    @property
    def url(self):
        url_template = r"https://www-947.ibm.com/support/entry/portal/wlup?serial={serial}&type={type}"
        return url_template.format(serial = self.serial, type = self.type)

    @property
    def header_data(self):
        if self._mem_header_data == {}:
            header_row = self.ibm_sys_tables[0].find('.//tbody/tr').findall('.//td')
            if not header_row:
                err_msg = "IBM Header Table in not found for tag %s"%self.tag
                logging.critical(err_msg)
                raise IBMDomChange(err_msg)
            model = header_row[1].text.strip()
            product_number = self.type+'-'+model
            self._mem_header_data['product_number'] = product_number
        return self._mem_header_data

    @property
    def detail_data(self):
        if self._mem_detail_data == []:

            data_table = self.ibm_sys_tables[self.INDEX_FOR_PRODUCT_DATA]
            for tr in data_table.findall('.//tbody/tr'):
                manf_part, fru_part, descr, serviceable =  [td.text.strip() for td in tr.findall('.//td/span')]

                self._mem_detail_data.append({'part_number': manf_part,
                                              'fru_part': fru_part,
                                              'description': descr,
                                              'qty': 1
                                             })
        return self._mem_detail_data


class ServerTagLookUp:

    def __init__(self, tags, manf):
        assert manf in ['hp', 'dell', 'ibm'], 'Unknown Manufacturer %s'%manf
        scrapers = {'hp': HPLookUp,
                    'dell': DellLookUp,
                    'ibm' : IBMLookUp}

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

