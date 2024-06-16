from pyhamtools import LookupLib, Callinfo

my_lookuplib = LookupLib(lookuptype="clublogxml", filename="data/clublog.xml")
cic = Callinfo(my_lookuplib)

#{'country': 'FEDERAL REPUBLIC OF GERMANY', 'adif': 230, 'cqz': 14, 'continent': 'EU', 'longitude': 10.0, 'latitude': 51.0}

def lookup(call, ts):
    try:
        return cic.get_all(call, ts)['adif']
    except:
        return None

def info(call, ts):
    try:
        return cic.get_all(call, ts)
    except:
        return None
