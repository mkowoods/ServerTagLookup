import oem_description_parser

__author__ = 'mwoods'

from google.appengine.ext import ndb, deferred
from google.appengine.api import memcache
#import item_master as oem
import oem_description_parser as odp
import hashlib
from os import path
import json
import logging
import time


IM_SHARDS = 10


STATIC_DIR = path.join(path.dirname(__file__), 'static')

ITEM_MASTER = json.load(open(STATIC_DIR+"/item_master_hp.json", "rb"))
ITEM_MASTER.update(json.load(open(STATIC_DIR+"/item_master_dell.json", "rb")))

# for i in range(IM_SHARDS):
#     tmp_im = json.load(open(STATIC_DIR+"/item_map_%d.json"%i, "rb"))
#     memcache.set('item_map_%d'%i, tmp_im)
#
# def sku_to_shard_id(oem_sku):
#     hash_id = int(hashlib.md5(oem_sku).hexdigest(), 16)%IM_SHARDS
#     return 'item_map_%d'%int(hash_id)
#
# def get_data(oem_sku):
#     val = memcache.get(sku_to_shard_id(oem_sku))
#     return val

###### Server Tag History Class and Related Methods ####
class ServerTagHistory(ndb.Model):
    create_date = ndb.DateTimeProperty(auto_now_add=True)
    manufacturer = ndb.StringProperty()
    tag = ndb.StringProperty()
    # data = ndb.JsonProperty()
    data = ndb.TextProperty()

    @staticmethod
    def add_tag(manf, tag, data):
        if type(data) != str:
            data = json.dumps(data)
        tag = ServerTagHistory(id = manf+'|'+tag,
                               manufacturer = manf,
                               tag = tag,
                               data = data)
        key = tag.put()
        return key

    @staticmethod
    def get_data(manf, tag):
        server = ServerTagHistory.get_by_id(manf+'|'+tag)
        if server is not None:
            return json.loads(server.data)

    @staticmethod
    def is_in_db(manf, tag):
        return ServerTagHistory.get_by_id(manf + '|' + tag) is not None



####Store JSON Item Master#####

class ItemMasterStorage(ndb.Model):
    """Each Entity Stores a JSON Blob that will be queried for later use
        The record stores it's shard number and a reference to the next "chunk" of data to be pulled to
        reconstruct the full set in a method similar to a linked list
    """
    create_date = ndb.DateTimeProperty(auto_now_add= True)
    label = ndb.StringProperty()
    shard = ndb.IntegerProperty()
    data = ndb.JsonProperty()  #schema: {sku : {'internal_sku': ..., 'manf': ..., 'desc': ..., 'comp_cls': ...}, sku : {...}, ...}

class ItemMasterAPI:

    def __init__(self):
        self.SHARDS = 10
        self.LABEL = 'item_map'
        self.ITEM_MASTER = ITEM_MASTER #TODO: need to refactor to the DB

    def get_datastore_id(self, idx):
        assert 0 <= int(idx) < self.SHARDS, 'index: %d, shards: %d'%(idx, self.SHARDS)
        return self.LABEL+'::'+str(idx)

    def sku_to_shard_idx(self, oem_sku):
        hash_id = int(hashlib.md5(oem_sku).hexdigest(), 16)%self.SHARDS
        return hash_id

    def get_datastore_id_from_sku(self, oem_sku):
        idx = self.sku_to_shard_idx(oem_sku)
        return self.get_datastore_id(idx)

    def get_subtype_from_item_master(self, oem_sku):
        _, _, subtype = self.ITEM_MASTER.get(oem_sku, (None, None, None))
        return subtype

    def get_sku(self, oem_sku):

        #set default variables
        internal_sku, comp_cls, source = None, None, None

        id = self.get_datastore_id_from_sku(oem_sku)
        im_ent = ItemMasterStorage.get_by_id(id)

        if im_ent and (oem_sku in im_ent.data):
            sku_data = im_ent.data[oem_sku]
            internal_sku = sku_data.get('internal_sku', None)
            comp_cls = sku_data.get('comp_cls', None)
        elif oem_sku in self.ITEM_MASTER:
            internal_sku = oem_sku
        if comp_cls is None:
            comp_cls = self.get_subtype_from_item_master(oem_sku)
            if not comp_cls:
                comp_cls = self.get_subtype_from_item_master(internal_sku)
        return (internal_sku, comp_cls, source)

    def update_item(self, sku, internal_sku, comp_cls):
        shard = self.get_datastore_id_from_sku(sku)
        logging.info('in ItemMasterAPI.update_shard shard: %s, sku: %s'%(str(shard), str(sku)))

        item_master_shard = ItemMasterStorage.get_by_id(shard)
        item_master_shard.data.setdefault(sku, {})
        item_master_shard.data[sku]['internal_sku'] = internal_sku
        item_master_shard.data[sku]['comp_cls'] = comp_cls

        _ = item_master_shard.put()
        return item_master_shard.data[sku]

    def delete_key(self, sku):
        shard = self.get_datastore_id_from_sku(sku)
        raise NotImplementedError()




###Store OEM Product Info and Mapping####

class OEMComponentDataBase(ndb.Model):
    create_date = ndb.DateTimeProperty(auto_now_add=True)
    manufacturer = ndb.StringProperty()
    oem_sku = ndb.StringProperty()
    oem_description = ndb.StringProperty()
    internal_sku = ndb.StringProperty()
    component_class = ndb.StringProperty()
    data_mapping_source = ndb.StringProperty()


class OEMCompDBAPI:

    """Class for handling OEM Component Mapping and interactions with the OEMComponentDataBase"""

    def __init__(self, manf, product, description):
        self.manf = manf
        self.product = product
        self.description = description
        self.mem = {}
        self.item_master = ItemMasterAPI()

    def get_id(self):
        return self.manf+'::'+self.product

    @property
    def product_detail(self):
        """if the value is included, then it runs through the search routine and returns the matching triplet
            (internal_sku, component_class, source)
          if no value is found return (None, None, None)
        """
        if 'product_detail' not in self.mem:
            self.mem['product_detail'] = self.item_master.get_sku(self.product) if self.is_included else (None, None, None)
        return self.mem.get('product_detail')

    @property
    def is_included(self):
        if 'is_included' not in self.mem:
            self.mem['is_included'] = odp.product_is_included(self.manf, self.description)
        return self.mem.get('is_included')



    def get_component(self):
        key = self.get_id()
        cached_result = memcache.get(key)
        if cached_result:
            return cached_result
        else:
            result = OEMComponentDataBase.get_by_id(key)
            if result:
                memcache.set(key, result)
                return result

    #TODO: Need to switch this to deferred exeution
    def set_component(self, description = None):

        internal_sku, component_class, source = self.product_detail

        #this can all be done in the background
        oem_part = OEMComponentDataBase(id = self.get_id(),
                                 manufacturer = self.manf,
                                 oem_sku = self.product,
                                 oem_description = description,
                                 internal_sku = internal_sku,
                                 component_class = component_class,
                                 data_mapping_source = source
                                 )
        key = oem_part.put()
        memcache.set(self.get_id(), oem_part)
        return oem_part




def tests():
    IM = ItemMasterAPI()
    def _test1():

        sub_type = IM.get_subtype_from_item_master("SV-EE310GEL1Y-2")

        assert sub_type == 'WARRANTY', 'subtype test failed'
        print 'test1 passed for subtype'

    def _test2():

        sku1, comp_cls, source = IM.get_sku('SV-EE310GEL1Y-2')
        sku2, comp_cls, source = IM.get_sku('436377-001')

        assert sku1 == 'SV-EE310GEL1Y-2', '_test2 failed, expected SV-EE310GEL1Y-2 from item_master got %s'%str(sku1)
        assert sku2 == 'DBP-HP-436377-001', '_test2 failed expected DBP-HP-436377-001 from mapping got %s'%str(sku2)

        print '_test2 passed for mapping'

    for f in [_test1, _test2]:
        f()













