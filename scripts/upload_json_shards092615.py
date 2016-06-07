import os
import pprint
import models

from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.ext import db
import json
import os


def test():
    label = 'test'
    shard = 0
    id = label + '::' + str(shard)
    im_obj = models.ItemMasterStorage(
                             id = id,
                             label = label,
                             shard = shard,
                             data = {'test':'ing shit out'}
                             )
    key = im_obj.put()
    print key


def production():
    SHARDS = 10
    LABEL = 'item_map'
    for shard in range(SHARDS):
        shard = str(shard)
        id = LABEL+'::'+shard
        print 'working on', id
        data = json.load(open('/item_map_backup/item_map_%s.json' % (shard), 'rb'))

        im = models.ItemMasterStorage(
            id = id,
            label = LABEL,
            shard = int(shard),
            data = data
        )

        key = im.put()
        print 'wrote', id, key

"""
to run on server

from scripts import upload_json_shards092615 as script
script.test()

"""