import server_tag_lookup as stl
import unittest


# TODO: Need to add more test case

class STLTestCases(unittest.TestCase):

    def test_redirect_url(self):
        url = "http://www.dell.com/support/home/us/en/19/product-support/servicetag/AAA/configuration?s=BSD"
        resp = stl.get_resp(url)
        self.assertNotEqual(resp.url, url, 'URL Returned should differ from original url per redirects')


    def test_dell_tag_DGDHXP1(self):
        #print 'running test for dell lookup'
        dell = stl.DellLookUp('DGDHXP1')
        shipping_data = dell.header_data['Shipping Date']
        data_len = len(dell.detail_data)
        actual, expected = (shipping_data, data_len), ('1/21/2011', 34)
        self.assertEqual(actual, expected,
                         'Attributes Don''t Match for DGDHXP1 \
                         Actual(product_number, detail_data_len): % s Expected: % s' \
                         % (str(actual), str(expected)))

    def test_ibm_tag_lookup_7944_KQ095DA(self):
        """Test for System Type Code: 7944 and Serial Number: KQ095DA"""
        # print 'running test for ibm lookup'
        ibm = stl.IBMLookUp("7944|KQ095DA")
        product_number = ibm.header_data['product_number']
        data_len = len(ibm.detail_data)
        actual, expected = (product_number, data_len), ('7944-AC1', 18)
        self.assertEqual(actual, expected,
                         'Attributes dont match for IBM Lookup, tag: 7944|KQ095DA \
                          Actual(product_number, detail_data_len): % s Expected: % s' \
                         % (str(actual), str(expected)))

    def test_hp_lookup_MXQ03402B7(self):
        """Test for HP API using tag MXQ03402B7 to verify"""
        # print 'running test for hp lookup'
        hp = stl.HPLookUp("MXQ03402B7")
        product_number = hp.header_data['product_number']
        data_len = len(hp.detail_data)
        actual = (product_number, data_len)
        expected = ('601361-001', 29)
        self.assertEqual(actual, expected,
                         'Attributes dont match for HP Lookup Tag MXQ03402B7. \
                         Actual(product_number, detail_data_len): %s \
                         Expected: %s' % (str(actual), str(expected)))


import sys

def execute_test_suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(STLTestCases)
    unittest.TextTestRunner(stream = sys.stdout, verbosity=2).run(suite)