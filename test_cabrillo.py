import rrlog.cabrillo as cabrillo
import datetime
import pytest

def test_cabrillo():
    assert cabrillo.parse("""
START-OF-LOG: 3.0
QSO: 3577 DG 2024-04-29 1912 DA0RR       -03 AO75GA       -17  IM79
END-OF-LOG:
""") == {
            'qsos': [{'freq': 3577, 'band': 80, 'mode': 'DG', 'ts': datetime.datetime(2024, 4, 29, 19, 12, tzinfo=datetime.timezone.utc),
                      'station_callsign': 'DA0RR', 'rsttx': '-03', 'extx': '',
                      'call': 'AO75GA', 'rstrx': '-17', 'exrx': 'IM79'}],
            'START-OF-LOG': '3.0',
            'QSO': '3577 DG 2024-04-29 1912 DA0RR       -03 AO75GA       -17  IM79'}

    assert cabrillo.parse("""
START-OF-LOG: 3.0
QSO: 3577 DG 2024-04-29 1912 DA0RR       -03  JO64 AO75GA       -17
END-OF-LOG:
""") == {
            'qsos': [{'freq': 3577, 'band': 80, 'mode': 'DG', 'ts': datetime.datetime(2024, 4, 29, 19, 12, tzinfo=datetime.timezone.utc),
                      'station_callsign': 'DA0RR', 'rsttx': '-03', 'extx': 'JO64',
                      'call': 'AO75GA', 'rstrx': '-17', 'exrx': ''}],
            'START-OF-LOG': '3.0',
            'QSO': '3577 DG 2024-04-29 1912 DA0RR       -03  JO64 AO75GA       -17'}

    assert cabrillo.parse("""
START-OF-LOG: 3.0
QSO:  7044 RY 2024-04-28 1701 DF5BX             001    DD7UW             001    
QSO:  7042 RY 2024-04-28 1702 DF5BX             002    DL3SYA            005    
END-OF-LOG:
""") == {
            'qsos': [{'freq': 7044, 'band': 40, 'mode': 'RY', 'ts': datetime.datetime(2024, 4, 28, 17, 1, tzinfo=datetime.timezone.utc),
                      'station_callsign': 'DF5BX', 'rsttx': None, 'extx': '001',
                      'call': 'DD7UW', 'rstrx': None, 'exrx': '001'},
                     {'freq': 7042, 'band': 40, 'mode': 'RY', 'ts': datetime.datetime(2024, 4, 28, 17, 2, tzinfo=datetime.timezone.utc),
                      'station_callsign': 'DF5BX', 'rsttx': None, 'extx': '002',
                      'call': 'DL3SYA', 'rstrx': None, 'exrx': '005'}],
            'START-OF-LOG': '3.0',
                     'QSO': '7044 RY 2024-04-28 1701 DF5BX             001    DD7UW             001\n7042 RY 2024-04-28 1702 DF5BX             002    DL3SYA            005'}

    assert cabrillo.parse("""
START-OF-LOG: 3.0
QSO: 3577 DG 2024-04-29 1902 DL3KWF       +14  JO64 OK2USM       +07  JN89 
QSO: 3577 DG 2024-04-29 1903 DL3KWF       +13  JO64 DO2SBS       +06  JO71 
QSO: 3577 DG 2024-04-29 1903 DL3KWF       +13  JO64 M0NPT        +11      
QSO: 3577 DG 2024-04-29 1912 DL3KWF       -03  JO64 AO75GA       -17      
END-OF-LOG:
""") == {'qsos': [{'freq': 3577, 'band': 80, 'mode': 'DG', 'ts': datetime.datetime(2024, 4, 29, 19, 2, tzinfo=datetime.timezone.utc),
                   'station_callsign': 'DL3KWF', 'rsttx': '+14', 'extx': 'JO64',
                   'call': 'OK2USM', 'rstrx': '+07', 'exrx': 'JN89'},
                  {'freq': 3577, 'band': 80, 'mode': 'DG', 'ts': datetime.datetime(2024, 4, 29, 19, 3, tzinfo=datetime.timezone.utc),
                   'station_callsign': 'DL3KWF', 'rsttx': '+13', 'extx': 'JO64',
                   'call': 'DO2SBS', 'rstrx': '+06', 'exrx': 'JO71'},
                  {'freq': 3577, 'band': 80, 'mode': 'DG', 'ts': datetime.datetime(2024, 4, 29, 19, 3, tzinfo=datetime.timezone.utc),
                   'station_callsign': 'DL3KWF', 'rsttx': '+13', 'extx': 'JO64',
                   'call': 'M0NPT', 'rstrx': '+11', 'exrx': ''},
                  {'freq': 3577, 'band': 80, 'mode': 'DG', 'ts': datetime.datetime(2024, 4, 29, 19, 12, tzinfo=datetime.timezone.utc),
                   'station_callsign': 'DL3KWF', 'rsttx': '-03', 'extx': 'JO64',
                   'call': 'AO75GA', 'rstrx': '-17', 'exrx': ''}],
         'START-OF-LOG': '3.0',
         'QSO': '3577 DG 2024-04-29 1902 DL3KWF       +14  JO64 OK2USM       +07  JN89\n3577 DG 2024-04-29 1903 DL3KWF       +13  JO64 DO2SBS       +06  JO71\n3577 DG 2024-04-29 1903 DL3KWF       +13  JO64 M0NPT        +11\n3577 DG 2024-04-29 1912 DL3KWF       -03  JO64 AO75GA       -17'}

    assert cabrillo.parse("""
START-OF-LOG: 3.0
QSO: 144000 CW 2024-03-16 1540 DF7C 559 001 A JO31HI DK5DQ   559 005 B JO31QH 0
END-OF-LOG:
""") == {'qsos': [{'freq': 144000, 'band': 2, 'mode': 'CW', 'ts': datetime.datetime(2024, 3, 16, 15, 40, tzinfo=datetime.timezone.utc),
                   'station_callsign': 'DF7C', 'rsttx': '559', 'extx': '001 A JO31HI',
                   'call': 'DK5DQ', 'rstrx': '559', 'exrx': '005 B JO31QH', 'trx': 0}],
         'START-OF-LOG': '3.0',
         'QSO': '144000 CW 2024-03-16 1540 DF7C 559 001 A JO31HI DK5DQ   559 005 B JO31QH 0'}

def test_errors():
    with pytest.raises(Exception):
        cabrillo.parse("""
QSO: 21034 CW 2024-05-01 1900 DK8ZZ         ZIK        DL    N1LN          BRUCE      1141  
QSO: 21031 CW 2024-05-01 1902 DK8ZZ         ZIK        DL    KH7X          MIKE   
""")
