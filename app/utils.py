from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def create_pdf(text, filename="summary.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()

    elements = []

    for line in text.split("\n"):
        elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 10))

    doc.build(elements)

    return filename