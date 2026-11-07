#!/usr/bin/python3

"""Parser for EDI contest logs (REG1TEST format).

The EDI (Electronic Data Interchange) format for IARU Region 1 contests
above 30 MHz is defined here:

    https://www.darc.de/fileadmin/_migrated/content_uploads/EDI_REG1TEST.pdf

An EDI file is three sections:

  * a header of ``Key=Value`` lines, starting with ``[REG1TEST;1]``,
  * an optional ``[Remarks]`` section,
  * a ``[QSORecords;N]`` section with N semicolon-separated QSO records.

The QSO record layout is (fields we use are named below):

    Date;Time;Call;Mode code;Sent-RST;Sent QSO number;Received-RST;
    Received QSO number;Received exchange;Received-WWL;QSO-Points;
    New-Exchange-(N);New-WWL-(N);New-DXCC-(N);Duplicate-QSO-(D)

This parser is deliberately forgiving: real logs are written by many
different programs, and some append non-standard trailers such as
``[END; UcxLog 8.15]``. Anything after the QSO records that does not
start with a date is ignored.
"""

import re
from datetime import datetime, timezone


# QSO record field indices, per the "QSO record definition" in the spec.
_F_DATE = 0
_F_TIME = 1
_F_CALL = 2
_F_MODE = 3
_F_RSTTX = 4
_F_EXTX = 5        # sent QSO number
_F_RSTRX = 6
_F_EXRX = 7        # received QSO number
_F_EXCH = 8        # received exchange
_F_WWL = 9         # received World Wide Locator
_F_POINTS = 10
_F_DUP = 14

_re_reg1test = re.compile(r'^\[REG1TEST;')
_re_qso_header = re.compile(r'^\[QSORecords;(\d+)\]')
_re_date = re.compile(r'^\d{6}$')


def _field(fields, index):
    """Return field `index`, or '' if the record is short.

    The spec allows trailing empty fields to be omitted, so indexing off
    the end of the split line is normal, not an error.
    """
    return fields[index] if index < len(fields) else ''


def _qso(fields):
    """Build one QSO dict from a split QSO record line."""
    date, time = _field(fields, _F_DATE), _field(fields, _F_TIME)
    ts = datetime.strptime(date + ' ' + time, '%y%m%d %H%M').replace(tzinfo=timezone.utc)

    # The received exchange is made up of the received QSO number and the
    # contest-specific exchange (e.g. a DOK); either may be empty.
    exrx = ' '.join(x for x in (_field(fields, _F_EXRX).strip(),
                                _field(fields, _F_EXCH).strip()) if x)

    return {
        'ts': ts,
        'call': _field(fields, _F_CALL).strip().upper(),
        'mode': _field(fields, _F_MODE).strip(),
        'rsttx': _field(fields, _F_RSTTX).strip(),
        'extx': _field(fields, _F_EXTX).strip(),
        'rstrx': _field(fields, _F_RSTRX).strip(),
        'exrx': exrx,
        'wwl': _field(fields, _F_WWL).strip().upper(),
        'points': _field(fields, _F_POINTS).strip(),
        'duplicate': _field(fields, _F_DUP).strip().upper() == 'D',
    }


def parse(edi):
    data = {'qsos': []}
    qsos = []
    remarks = []
    in_remarks = False
    in_qsos = False

    for line in edi.splitlines():
        line = line.rstrip('\r')  # tolerate CRLF and mixed line endings

        if not in_qsos:
            if line.startswith('['):
                m = _re_qso_header.match(line)
                if m:
                    data['QSORECORDS'] = int(m.group(1))
                    in_qsos = True
                    in_remarks = False
                elif line.startswith('[Remarks]'):
                    in_remarks = True
                # [REG1TEST;...] and any other marker: ignore
                continue
            if in_remarks:
                remarks.append(line.strip())
                continue
            if line.strip() == '':
                continue
            field, sep, value = line.partition('=')
            if sep:
                data[field.strip().upper()] = value.strip()
            continue

        # QSO section. Tolerate blank lines and trailers like "[END; ...]".
        if not _re_date.match(line.partition(';')[0]):
            continue
        fields = line.split(';')
        if _field(fields, _F_CALL).strip().upper() == 'ERROR':
            continue  # error placeholder record, not a real QSO
        qsos.append(_qso(fields))

    data['qsos'] = qsos
    if remarks:
        remarks = '\n'.join(remarks).strip()
        if remarks:
            data['REMARKS'] = remarks
    return data


if __name__ == '__main__':
    import sys
    print(parse(sys.stdin.read()))
