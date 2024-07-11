from io import BytesIO
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

width, height = 297*mm, 210*mm
pdfmetrics.registerFont(TTFont('Avenir Next Condensed Regular', 'rrmember/data/avenir-next-condensed-regular.ttf'))
name_ptsize = 36 # 152 pixel
date_ptsize = 10 # 43 pixel

def letterspace(text):
    return ' '.join(text)

def certificate(call, name, date, member_no):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setTitle(f"RRDXA Membership Certificate of {call}")

    # president signature is using font "A Handwriting"
    c.drawImage("rrmember/data/rrdxa-urkunde-df7ee.jpg", 0, 0, width=width, height=height)

    c.setFillColor('#BCBCBC')
    c.setFont('Avenir Next Condensed Regular', name_ptsize)
    c.drawCentredString(width/2, 65*mm, letterspace(f"{name}, {call}".upper()))
    c.setFont('Avenir Next Condensed Regular', date_ptsize)
    c.drawCentredString(84*mm, 23*mm, letterspace(date))
    c.drawCentredString(143*mm, 23*mm, letterspace(str(member_no)))

    c.showPage()
    c.save()
    return buf.getvalue()

if __name__ == '__main__':
    import sys
    #pdf = certificate('DF7CB', 'Christoph Berg', '2024-03-24', 999)
    pdf = certificate(*sys.argv[1:])
    sys.stdout.buffer.write(pdf)
