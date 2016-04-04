import json


"""
    W347K, 507127-B21
"""

#TODO: https://twitter.github.io/typeahead.js/examples/
#TODO: http://scottlobdell.me/2015/02/writing-autocomplete-engine-scratch-python/

class HDDSearchEngine:

    def __init__(self):
        self.HDD_DATA = json.load(open('./item_search_tables/hdd.json', 'rb'))
        self.FIELDS_FOR_COMPATIBILITY = ['DISK_SPEED', 'DISK_SPEED_UOM',
                                         'FORM_FACTOR', 'VENDOR',
                                         'STORAGE_SIZE', 'STORAGE_SIZE_UOM',
                                         'TRANSFER_RATE', 'TRANSFER_RATE_UOM',
                                         'CONNECTION_TYPE']

    def write_tokens(selfs):
        """
            function to take the search data and create a search index of tokens to rows to enable interactive search
            should hoist that into memcache
        """
        raise  NotImplementedError

    def get_part(self, part):
        return self.HDD_DATA.get(part)

    def and_query(self, search_parameters):
        """
            search_parameters: dict of {field_names : attribute value}
            The function returns a list of dictionaries where each dictionary
            is a record for a part with associated attributes
        """
        results = []
        if len(search_parameters) == 0:
            return results

        for line in self.HDD_DATA.values():
            if all([line[k] == v  for k,v in search_parameters.items()]):
                results.append(line)
        return results

    def get_search_parameters_for_compatibility(self, part):
        data = self.get_part(part)
        query_dict = {}
        if data:
            query_dict = {field: data[field] for field in self.FIELDS_FOR_COMPATIBILITY }
        return query_dict

    def get_all_exactly_compatible_parts(self, part):
        """
            returns all parts that match the given part on the different fields determining compatible
        """
        search_parameters = self.get_search_parameters_for_compatibility(part)
        return self.and_query(search_parameters)





"""
### create a bag of tokens to store all the values ###
TOKEN_TO_ROW_MAP = {}
for idx, row in enumerate(TABLE):
    for field in FIELDS_FOR_COMPATIBILITY:
        tokens = row[field].split()
        for token in tokens:
            if token in TOKEN_TO_ROW_MAP:
                TOKEN_TO_ROW_MAP[token].add(idx)
            else:
                TOKEN_TO_ROW_MAP[token] = set([idx])
"""





