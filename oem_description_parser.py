__author__ = 'mwoods'



def _check_is_included_dell(description_list):
    """basic if-then tree to work through the list of ASSEMBLY descriptors and flag
    those that would not be included
    """
    #print description_list
    EXCLUDED_DESC_PREFIXES_DELL = set(['KEYBOARD', 'DISPLAY', 'LABEL',
                                      'INFORMATION', 'BATTERY',
                                      'SCREW', 'INSTRUCTION',
                                      'CORD', 'GUIDE', 'KIT',
                                      'PLACEMAT', 'CABLE'])

    term1 = description_list[0]
    if term1 in EXCLUDED_DESC_PREFIXES_DELL:
        return False
    #HANDLE Assembly Items
    elif term1 == 'ASSEMBLY':
        term2 = description_list[1]
        if term2 in set(['BEZEL', 'CABLE', 'PRINTED', 'LABEL', 'BRACKET']):
            return False
    elif term1 == 'MODULE':
        term2 = description_list[1]
        if term2 in set(['SOFTWARE', 'INFORMATION', 'CABLE', 'BEZEL', 'CORD', 'INFORMATION', 'FILLER']):
            return False
    #Filter out 2 tuples
    elif tuple(description_list[:2]) in set([('SERVICE', 'CHARGE'), ('SHIPPING', 'MATERIAL'),
                                             ('TECHNICAL', 'SHEET'), ('PREPARATION', 'MATERIAL'),
                                             ('SHIP', 'GROUP'), ('OVERPACK', 'KIT')]):
        return False
    return True


def _check_is_included_hp(description_list):
    """basic if-then tree to work through the list of ASSEMBLY descriptors and flag
    those that would not be included
    """
    EXCLUDED_DESC_PREFIXES_HP = set(['LBL', 'BADGE', 'CARD', 'CORD', 'CUSHION'
                                 'SLIDE ASSY', 'VELCRO', 'CA', 'CABLE', 'WASHER', 'TIE', 'SCREW',
                                 'BOX', 'SOFTWARE', 'BAG', 'SCR', 'BLNK', 'CORR', '[TMP', '[ORD'])
    term1 = description_list[0]
    if term1 in EXCLUDED_DESC_PREFIXES_HP:
        return False
    elif term1 == 'ASSY':
        term2 = description_list[1]
        if term2 in set(['BLANK', 'BOX', 'RFID', 'CORD']):
            return  False

    elif tuple(description_list[:2]) in set([('SLIDE', 'ASSY'), ('FRONT', 'CUSHION'), ('BACK', 'CUSHION'),
                                             ('HP', 'ZPKG')]):
        return False

    return True


def product_is_included(manf, description):
    description = description.upper()
    desc_list = description.replace(",", " ").split()

    if manf == "dell":
        return _check_is_included_dell(desc_list)

    elif manf == "hp":
        if description in set(['SKU DESC NOT AVAILABLE', 'ENCLOSURE ASSEMBLY']):
            return False
        else:
            return _check_is_included_hp(desc_list)

    return True
