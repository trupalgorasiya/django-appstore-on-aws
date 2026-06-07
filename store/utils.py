from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_order_confirmation_email(order):
    subject = f"Order Confirmation - #{order.id}"

    html_content = render_to_string(
        "emails/order_confirmation.html",
        {"order": order}
    )

    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [order.email]
    )

    email.attach_alternative(html_content, "text/html")
    email.send()


def send_order_status_update_email(order):
    subject = f"Order #{order.id} Status Updated"

    html_content = render_to_string(
        "emails/order_status_update.html",
        {"order": order}
    )

    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [order.email]
    )
    
    email.attach_alternative(html_content, "text/html")
    email.send()
# store/utils.py

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.http import HttpResponse
from django.conf import settings
from datetime import datetime
import os


# =====================================================
# 📧 ORDER STATUS EMAIL FUNCTION (YOUR EXISTING ONE)
# =====================================================

def send_order_status_update_email(order):
    # keep your existing email code here
    pass


# =====================================================
# 📄 REUSABLE PDF GENERATOR
# =====================================================

def generate_pdf(title, headers, rows):

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{title}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=40,
        bottomMargin=40,
    )

    elements = []
    styles = getSampleStyleSheet()

    # ===== Register Font for ₹ Support =====
    # font_path = os.path.join(settings.BASE_DIR, "store/static/fonts/NotoSans-Regular.ttf")
    # pdfmetrics.registerFont(TTFont("NotoSans", font_path))

    # ===== Header =====
    elements.append(Paragraph("<b>JVJ Enterprise</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    generated_date = datetime.now().strftime("%d %B %Y %I:%M %p")
    elements.append(Paragraph(f"Generated On: {generated_date}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # ===== Table =====
    table_data = [headers] + rows

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#6366f1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))

    elements.append(table)

    # ===== Footer =====
    def add_footer(canvas_obj, doc):
        page_num = canvas_obj.getPageNumber()
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawString(30, 20, "This is a system generated report.")
        canvas_obj.drawRightString(200 * mm, 20, f"Page {page_num}")

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)

    return response