import server_tag_lookup as stl
import json
# import openpyxl
import csv
import pprint

sample_data = json.load(open('sample_api_output.json', 'rb'))
res = sample_data[0]


def server_table(tag_data):
    # print tag_data.keys()
    # System level
    rows = []
    try:
        rows.append(['', 'Product Number', tag_data['product_number']])
    except:
        pprint.pprint(tag_data)

    rows.append(['', 'Tag', tag_data['tag']])
    rows.append([''])

    # Component Level
    rows.append(['', 'Part Number', 'Qty', 'Category SubType', 'Description'])

    for item_dict in tag_data['components']:
        if item_dict['is_included']:
            rows.append(['',
                         item_dict['part_number'],
                         item_dict['qty'],
                         item_dict['cat_sub_type'],
                         item_dict['description']
                         ])

    return rows


def process_quote(quote_data):
    """
        quote_data: list of tag_data dicts such as can be found in the results of the server_tag_api
    """
    rows = []
    for line in quote_data:
        # pprint.pprint(line)
        rows.extend(server_table(line))
        rows.append([''])
        rows.append([''])
    return rows


def run_test():
    manf = 'dell'
    tags = [
        'DGDHXP1',
        #       '9DKYWQ1',
        #      '978SRR1',
        'HHXC0L1'
    ]

    servers = stl.ServerTagLookUp(tags=tags, manf=manf)
    data = servers.results
    print len(data)
    # json.dump(data, open('sample_eq_tuning.json'))
    rows = process_quote(data)
    return rows
