#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import json
import logging
import models
import server_tag_lookup as stl
import item_search as search
from google.appengine.api import memcache
import csv
import enriched_quote as eq

#TODO: Create GLOBAL Variable to track when the last time the api was called to determine if someone is curently sending a request


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=False)


class Handler(webapp2.RequestHandler):
    """Wrapper for Common Functions Used in rendering pages"""
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def get(self, *a, **kw):
        return self.request.get(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_json(self, obj, status = 200):
        self.response.status = status
        self.response.headers['Content-Type'] = "application/json"
        self.write(json.dumps(obj, indent=4, separators=(',', ': ')))


class MainHandler(Handler):
    def get(self):
        self.render('index.html')


class AdminHandler(Handler):
    #TODO: need to do authentication for admin screen based on signed in username
    """Basic Admin Screen for testing certain aspects of the algorithm"""
    def get(self):
        self.render('admin.html')


class ItemSarchPage(Handler):
    """
        Handle Item Relationship LookUp
    """
    def get(self):
        self.render('item_search.html')


class ServerTagLookUpAPI(Handler):
    """
       Defines Class for the Server Tag Lookup API that's found @ "/server_tag_api
       the lookup takes as input a server tag (chassis code) and a manf ("hp", "dell" as of 09/06/15)
    """

    def get_json_payload_from_site(self, tag, manf):
        #TODO: Should do basic validation of inputs before moving using assert

        json_payload = None
        error_payload = None
        status_code = 200

        try:
            lookup = stl.ServerTagLookUp([tag], manf)
            json_payload = lookup.results
        except ValueError as err:
            error_payload = {'tag': tag, 'message': str(err.message)}
            logging.error('Value Error Raise on Tag: %(tag)s, Arg: %(message)s' % error_payload)
        except stl.DellDomChange as err:
            error_payload= {'tag': tag, 'message': str(err.message)}
            logging.error('DellDomChange Error Raised on Tag: %(tag)s, Message: %(message)s' % error_payload)
        except stl.DellTagNotFound as err:
            error_payload = {'tag' : tag, 'message' : str(err.message)}
            logging.error('DellTagNotFound Error Raised on Tag: %(tag)s, Message: %(message)s' % error_payload)
        except Exception as err:
            error_payload = {'type': str(err.__class__), 'message' : str(err.message), 'tag': tag, 'manf': manf}
            logging.exception('Unexpected Exception Type: %(type)s, Message: %(message)s, tag: %(tag)s, manf: %(manf)s' % error_payload)

        if json_payload is None:
            json_payload = [{'tag': tag,
                            'product_number': None,
                            'components' : [],
                             'message' : error_payload['message']
                            }]
            status_code = 400
        return json_payload, status_code

    def get_json(self, tag, manf):
        key = manf+"|"+tag
        cached_data = memcache.get(key)
        if cached_data:
            return cached_data, 200
        else:
            data, status_code = self.get_json_payload_from_site(tag, manf)
            if status_code == 200:
                memcache.set(key, data)
            return data, status_code

    def get(self):
        tag = self.request.get('server_tag')
        manf = self.request.get('manf')
        if tag == 'test':
            return self.render_json(json.load(open('sample_dell_output.json', 'rb'))[0])

        json_payload, status = self.get_json(tag, manf)

        return self.render_json(json_payload, status)


class ItemMasterLookupAPI(Handler):

    def get(self):

        im = models.ItemMasterAPI()
        sku = self.request.get('sku').upper()

        data = {}
        data['sku'] = sku
        data['internal_sku'], data['comp_cls'], _ = im.get_sku(sku)
        data['shard'] = im.get_datastore_id_from_sku(sku)
        return self.render_json(data, 200)

    def post(self):
        im = models.ItemMasterAPI()
        sku = self.request.get('sku').upper()
        internal_sku = self.request.get('internal_sku').upper()
        comp_cls = self.request.get('comp_cls').upper()

        prior_internal_sku, prior_comp_cls, _ = im.get_sku(sku)

        logging.info('Updating Entry')
        logging.info('Prior Data: ' + str((sku, prior_internal_sku, prior_comp_cls)))

        res = im.update_item(sku, internal_sku, comp_cls)

        logging.info('Updated Entry: '+str((sku, res['internal_sku'], res['comp_cls'])))

        return self.render_json(res, 200)


class ItemRelationshipSearchAPI(Handler):

    def get(self):
        search_engine = search.HDDSearchEngine()

        sku = self.request.get('sku')
        search_type = self.request.get('search-type')

        if search_type == 'get-part':
            return self.render_json(search_engine.get_part(sku), 200)
        elif search_type == 'get-directly-compatible-parts':
            return self.render_json(search_engine.get_all_exactly_compatible_parts(sku), 200)


class QuotePageHandler(Handler):
    def get(self):
        # TODO: Need to handle upload of quote file and storage to the db
        # TODO: Need to enque the job so that it begins downloading the tags in the background
        # TODO: Need to determine way to save and render excel files
        # TODO: Need to keep a log of quotes that are avaialable for download
        return self.render('enrich_quotes.html')


class DownloadQuoteHandler(Handler):
    def get(self):
        quote_name = self.request.get('quote_name')
        if quote_name == 'test':
            rs = eq.run_test()

        self.response.headers['Content-Type'] = 'text/csv'
        self.response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
        writer = csv.writer(self.response.out)
        writer.writerows(rs)








app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/search', ItemSarchPage),
    ('/server_tag_api', ServerTagLookUpAPI),
    ('/item_master_api', ItemMasterLookupAPI),
    ('/item_search_api', ItemRelationshipSearchAPI),
    ('/quote_page', QuotePageHandler),
    ('/download_quote', DownloadQuoteHandler),
    ('/admin', AdminHandler)
], debug=True)


