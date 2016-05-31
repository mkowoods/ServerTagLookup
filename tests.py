import server_tag_lookup as stl
import unittest


class STLTestCases(unittest.TestCase):

    def test_redirect_url(self):
        url = "http://www.dell.com/support/home/us/en/19/product-support/servicetag/AAA/configuration?s=BSD"
        resp = stl.get_resp(url)
        self.assertNotEqual(resp.url, url, 'URL Returned should differ from original url per redirects')


    def test_dell_tag_DGDHXP1(self):
        dell = stl.DellLookUp('DGDHXP1')
        shipping_data = dell.header_data['Shipping Date']
        data_len = len(dell.detail_data)
        self.assertEqual((shipping_data, data_len), ('1/21/2011', 34), 'Attributes Don''t Match for DGDHXP1')

import sys

def execute_test_suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(STLTestCases)
    unittest.TextTestRunner(stream = sys.stdout, verbosity=2).run(suite)