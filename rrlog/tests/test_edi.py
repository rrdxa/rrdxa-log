"""Unit tests for the EDI (REG1TEST) parser and its band/mode maps.

The parser tests are pure (no database, no ``country`` lookup). Real
sample logs live in ``test/edi/`` alongside the Cabrillo fixtures in
``test/cabrillo/``.
"""
import datetime
from pathlib import Path

import pytest

import rrlog.edi as edi
from rrlog.edi_upload import bands, band_from_pband, modes

FIXTURES = Path(__file__).resolve().parents[2] / 'test' / 'edi'

HEADER = """\
[REG1TEST;1]
TName=IARU1 VHF
TDate=20230902;20230903
PCall=OE4EIE
PWWLo=JN87CE
PExch=JN87CE
PSect=SINGLE-OP
PBand=145 MHz
PClub=ADL604
MOpe1=OE4EIE
MOpe2=
CQSOs=2;1
CToSc=10882
CODXC=DL0GM;JO31UB;754
"""


def test_parse():
    data = edi.parse(HEADER + """\
[Remarks]
Nice contest, lots of Aurora.
[QSORecords;3]
230902;1838;OL3Z;1;59;001;59;332;;JN79FX;337;;N;N;
230902;1840;dl0gm;2;599;002;599;754;B;JO31UB;754;N;N;N;
230902;1850;ERROR;;;003;;;;;0;;;;
""")

    assert data['QSORECORDS'] == 3
    assert data['PCALL'] == 'OE4EIE'
    assert data['TNAME'] == 'IARU1 VHF'
    assert data['REMARKS'] == 'Nice contest, lots of Aurora.'
    # the ERROR placeholder is not a QSO
    assert len(data['qsos']) == 2

    assert data['qsos'][0] == {
        'ts': datetime.datetime(2023, 9, 2, 18, 38, tzinfo=datetime.timezone.utc),
        'call': 'OL3Z', 'mode': '1',
        'rsttx': '59', 'extx': '001',
        'rstrx': '59', 'exrx': '332',
        'wwl': 'JN79FX', 'points': '337', 'duplicate': False,
    }

    # callsigns and locators are normalised to upper case; the received
    # exchange combines the received QSO number and the exchange column
    assert data['qsos'][1]['call'] == 'DL0GM'
    assert data['qsos'][1]['wwl'] == 'JO31UB'
    assert data['qsos'][1]['exrx'] == '754 B'

    # no [Remarks] section at all -> no REMARKS key
    assert 'REMARKS' not in edi.parse(HEADER + "[QSORecords;0]\n")


def test_tolerates_crlf_and_trailer():
    text = (HEADER + "[QSORecords;1]\r\n"
            "230902;1838;OL3Z;1;59;001;59;332;;JN79FX;337;;N;N;\r\n"
            "[END; UcxLog 8.15]\r\n")
    data = edi.parse(text)
    assert len(data['qsos']) == 1
    assert data['qsos'][0]['call'] == 'OL3Z'


def test_duplicate_records_are_imported():
    data = edi.parse(HEADER + """\
[QSORecords;2]
230902;1838;OL3Z;1;59;001;59;332;;JN79FX;337;;N;N;
230902;1900;OL3Z;1;59;003;59;333;;JN79FX;0;;;;D
""")
    # duplicate-marked records are still real contacts for a logbook
    assert len(data['qsos']) == 2
    assert data['qsos'][1]['duplicate'] is True


def test_short_records():
    # trailing empty fields may be omitted entirely
    data = edi.parse(HEADER + "[QSORecords;1]\n230902;1838;OL3Z;2;599\n")
    assert data['qsos'][0]['call'] == 'OL3Z'
    assert data['qsos'][0]['exrx'] == ''
    assert data['qsos'][0]['wwl'] == ''


def test_bands():
    assert band_from_pband('145 MHz') == '2m'
    assert band_from_pband('50 MHz') == '6m'
    assert band_from_pband('435 MHz') == '70cm'
    assert band_from_pband('1,3 GHz') == '23cm'  # German decimal comma
    assert band_from_pband('1.3 GHz') == '23cm'
    assert set(bands.values()) <= set(__import__('rrlog.utils', fromlist=['all_bands']).all_bands)
    with pytest.raises(Exception):
        band_from_pband('11 m')


def test_modes():
    assert modes['1'] == ('PHONE', 'SSB', None)
    assert modes['2'] == ('CW', 'CW', None)
    assert modes['3'] == ('PHONE', 'SSB', None)  # cross mode, filed by TX mode
    assert modes['4'] == ('CW', 'CW', None)
    assert modes['9'] == ('DIGI', 'ATV', None)


@pytest.mark.parametrize('filename, count, band', [
    ('OE4EIE-432-mai23.EDI', 33, '70cm'),
    ('OE4EIE-04092021-145.EDI', 116, '2m'),
])
def test_fixtures(filename, count, band):
    data = edi.parse((FIXTURES / filename).read_text())
    assert data['QSORECORDS'] == count
    assert len(data['qsos']) == count
    assert band_from_pband(data['PBAND']) == band
    assert data['PCALL'] == 'OE4EIE'
    # every record has a timestamp and an upper-case call
    for qso in data['qsos']:
        assert qso['ts'].tzinfo is not None
        assert qso['call'] == qso['call'].upper()
