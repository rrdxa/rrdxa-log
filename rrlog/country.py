from pyhamtools import LookupLib, Callinfo

my_lookuplib = LookupLib(lookuptype="clublogxml", filename="data/clublog.xml")
cic = Callinfo(my_lookuplib)

def lookup(call, ts):
    #{'country': 'FEDERAL REPUBLIC OF GERMANY', 'adif': 230, 'cqz': 14, 'continent': 'EU', 'longitude': 10.0, 'latitude': 51.0}
    try:
        return cic.get_all(call, ts)['adif']
    except:
        return None
