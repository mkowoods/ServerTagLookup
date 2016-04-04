
__author__ = 'mwoods'
import json
import logging
import hashlib

from google.appengine.api import memcache

from os import path

from oem_description_parser import product_is_included


#CSU_TO_CURV_PART_MAP = json.load(open(STATIC_DIR+"/redirect_csu_to_curv.json", 'rb'))
#ITEM_SEARCH_BASE = json.load(open(STATIC_DIR+"/item_search_base_filtered.json", 'rb')) #filtered for only lines that appear in the part map

IM_SHARDS = 10

import time
start = time.time()
for i in range(IM_SHARDS):
    tmp_im = json.load(open(STATIC_DIR+"/item_map_%d.json"%i, "rb"))
    memcache.set('item_map_%d'%i, tmp_im)
logging.info('time to load file item_maps: %.2f'%(time.time() - start))

def sku_to_shard_id(oem_sku):
    hash_id = int(hashlib.md5(oem_sku).hexdigest(), 16)%IM_SHARDS
    return 'item_map_%d'%int(hash_id)

def get_subtype_from_item_master(product):
    return ITEM_MASTER.get(product, [None, None, None])[2]

def get_sku(oem_sku):
    val = memcache.get(sku_to_shard_id(oem_sku))
    internal_sku, comp_cls, source = None, None, None
    if val and (oem_sku in val):
        internal_sku = val[oem_sku]["internal_sku"]
    elif oem_sku in ITEM_MASTER:
        internal_sku = oem_sku
    comp_cls = get_subtype_from_item_master(oem_sku)
    return (internal_sku, comp_cls, source)


#def in_item_master(product):
#    return product in ITEM_MASTER

# def get_item_from_item_search_base(item):
#     for line in ITEM_SEARCH_BASE:
#         if line['item'] == item:
#             return line


# def search_item_search_base(product):
#     for line in ITEM_SEARCH_BASE:
#         descr = line['description']
#         item = line['item']
#         comp_class = line['comp_class']
#         if re.search('(^|\s)' + product + '(\s|$)', descr):
#             #print 'found product in item_search_base', item, product
#             if item in CSU_TO_CURV_PART_MAP:
#                 internal_sku = CSU_TO_CURV_PART_MAP[item]
#                 #print 'found product in CSU_TO_CURV_MAP', item, internal_sku
#                 return (internal_sku, comp_class, 'CSU Item Base to Curvature')
#     return (None, None, None)


# def blind_search(product):
#     """Searches each data sources and within strings. Can be unnecessarily CPU intensive.
#         Should plan on replacing with a key-value lookup
#     """
#
#     if product in ITEM_MASTER:
#         return (product, ITEM_MASTER[product][2], 'Item Master')
#     elif product in CSU_TO_CURV_PART_MAP:
#         internal_sku = CSU_TO_CURV_PART_MAP[product]
#         component_class = ITEM_MASTER.get(internal_sku, (None, None, None))[2]
#         return (internal_sku, component_class, 'CSU_TO_CURV_MAP')
#     else:
#         internal_sku = search_item_search_base(product)
#         return internal_sku



if __name__ == "__main__":
    import time
    import json
    manf = 'hp'
    labels = json.load(open('sample_hp_labels.json', 'rb'))
    labels.sort()
    print len(labels)

    start = time.time()
    ct = 0
    for desc in labels:
        print product_is_included(manf, desc), desc


    print time.time() - start, ct






