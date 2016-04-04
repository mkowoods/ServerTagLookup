"""
Goal: This program is designed to read in standard outputs from IBM systems and format/group the data into
a csv for easier processing.

"""


import os
import re




REGEX = '(Memory Module|CPU|HDD|CDROM|NIC|TapeDrive) (#\d{1,2}) (\w+)'

CPU_ATTRS = ['Name']
MEMORY_ATTRS = ['PartNumber', 'DeviceLocator', 'Capacity', 'Speed']
HDD_ATTR = ['Model', 'Size']
CDROM_ATTR = ['Name']
NIC_ATTR = ['Name']
TAPE_ATTR = ['Name']

CAT_ATTRS = {'CPU': CPU_ATTRS,
             'Memory Module' : MEMORY_ATTRS,
             'HDD' : HDD_ATTR,
             'CDROM' : CDROM_ATTR,
             'NIC' : NIC_ATTR,
             'TapeDrive' : TAPE_ATTR
             }

#GLOBAL_CATS = []


class IBMParser:
    def __init__(self, file_name):
        self.regex = REGEXq
        self.file_name = file_name
        self.system_name = None
        self.sytem_model = None
        self.components = {}

        with open(file_name, 'r') as data:
            tmp = data.readlines()
            for line in tmp:
                sys_line = line.rstrip().split('\t')
                if len(sys_line) < 2:
                    sys_line = [sys_line[0], '']
                self.add_to_component_dictionary(sys_line)



    def add_to_component_dictionary(self, line):
        try:
            label, val = line

        except:
            print repr(line)


        if val in ("N/A", "Not Specified"):
            pass
        elif label.startswith('ComputerSystem Name'):
            self.system_name = val

        elif label.startswith('ComputerSystem Model'):
            self.sytem_model = val
        else:
            res = re.match(REGEX, label)
            def _update_dict(cat, k, attr):
                self.components.setdefault(cat, {})
                self.components[cat].setdefault(k, {})
                self.components[cat][k][attr] = val

            if res:
                cat, k, attr = res.groups()
                attributes = CAT_ATTRS.get(cat, [])
                if attr in attributes:
                    _update_dict(cat, k, attr)

    def get_lines(self):
        output = []
        for cat, lines in self.components.items():
            for idx, attrs in lines.items():
                row = [self.file_name, self.system_name, self.sytem_model, cat, idx]
                row.append(' // '.join([attrs.get(attr, '') for attr in CAT_ATTRS[cat]]))
                output.append(row)
        if len(output) == 0:
            output = [[self.file_name, self.system_name, self.sytem_model, '', '', '']]
        return output



if __name__ == "__main__":
    import pprint
    import csv



    with open('tmp.csv', 'w') as f:
        csv_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        csv_writer.writerow(['filename', 'system_name', 'system_model', 'cat', 'idx', 'desc'])

        files = [f for f in os.listdir('.') if f.endswith('columns.txt')]
        for file_name in files:
            sys = IBMParser(file_name = file_name)
            print 'file_name: ', sys.file_name
            print 'system_name: ', sys.system_name
            csv_writer.writerows(sys.get_lines())

