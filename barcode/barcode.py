from reportlab.graphics.barcode import code39, code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

c = canvas.Canvas("barcode_example.pdf", pagesize=A4)

code_list = [
    'MANDOCMP', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456',
    '123456789', '987654321', '349871637',
    '897645362', '761239403', '891237456']

code_list = ['','','CMP0043','CMP0018','CMP0024','CMP0063','CMP0064','ORG0001','ORG0018','ORG0017']

x = 1 * mm
y = 285 * mm
x1 = 6.4 * mm

for code in code_list:
    #barcode = code39.Extended39("MANDOCMP")
    barcode = code128.Code128("MANDO"+code)
    if code!='':
        barcode.drawOn(c, x, y)

    x1 = x + 5.4 * mm
    y = y - 5 * mm
    if code!='':
        c.drawString(x1, y, "MANDO"+code)
    x = x
    y = y - 13.5 * mm

    if int(y) <= 0:
        x = x + 35 * mm
        y = 285 * mm
    print str(x)+" <> "+str(y)
c.showPage()
c.save()