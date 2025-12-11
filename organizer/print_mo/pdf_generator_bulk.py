# pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Flowable, KeepInFrame
from reportlab.graphics.barcode import code128
from io import BytesIO
from datetime import datetime
from typing import Union, List
import logging
import math


class DateFormatter:
    """Utility class for date formatting"""

    @staticmethod
    def format_date(date_value: Union[str, int, float, None]) -> str:
        """Convert date value to readable format"""
        if not date_value:
            return "Not specified"

        try:
            if isinstance(date_value, str):
                try:
                    # First try parsing as a datetime string
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').strftime('%a %b %d %Y')
                except ValueError:
                    # Then try parsing as Unix timestamp
                    try:
                        return datetime.fromtimestamp(float(date_value)).strftime('%a %b %d %Y')
                    except ValueError:
                        return date_value
            elif isinstance(date_value, (int, float)):
                # Handle numeric timestamp
                return datetime.fromtimestamp(float(date_value)).strftime('%a %b %d %Y')
            return str(date_value)
        except Exception as e:
            logging.error(f"Error formatting date: {str(e)}")
            return "Date Error"



class BarCode128(Flowable):
    """A custom Flowable for Code 128 barcodes"""

    def __init__(self, value, width=3 * inch, height=0.5 * inch):
        Flowable.__init__(self)
        self.value = value
        self.barWidth = width
        self.barHeight = height

    def wrap(self, availWidth, availHeight):
        """Returns the size this flowable will take up"""
        return self.barWidth, self.barHeight

    def draw(self):
        """Draw the barcode"""
        barcode = code128.Code128(self.value, barWidth=0.01 * inch, barHeight=self.barHeight)
        x = (self.barWidth - barcode.width) / 2  # Center the barcode
        barcode.drawOn(self.canv, x, 0)


class Checkbox(Flowable):
    """A custom Flowable for checkboxes"""

    def __init__(self, size=20):
        Flowable.__init__(self)
        self.size = size
        self.width = self.height = size

    def draw(self):
        self.canv.saveState()
        self.canv.setLineWidth(1)
        self.canv.rect(0, 0, self.size, self.size)
        self.canv.restoreState()


class PDFGenerator:
    """Class for generating PDF reports of Manufacturing Order data"""

    def __init__(self):
        # Get base styles
        self.styles = getSampleStyleSheet()

        # Title style with modern typography
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2C3E50')
        )

        # Code style for MO numbers
        self.code_style = ParagraphStyle(
            'CustomCode',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=1,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )

        # Date style with subtle appearance
        self.date_style = ParagraphStyle(
            'CustomDate',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=1,
            spaceAfter=15,
            textColor=colors.HexColor('#7F8C8D')
        )

        # Section subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#34495E')
        )

        # Table cell style
        self.cell_style = ParagraphStyle(
            'CustomCell',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=1
        )

        # Item style for parts table
        self.item_style = ParagraphStyle(
            'ItemCell',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#2C3E50')
        )

        # Header style for tables
        self.header_style = ParagraphStyle(
            'HeaderCell',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2C3E50')
        )

    def create_combined_pdf(self, mos: List) -> bytes:
        """Generate a combined PDF report for multiple manufacturing orders"""
        buffer = BytesIO()

        # Create the PDF document with reduced margins for better space usage
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        elements = []

        # Process each manufacturing order
        for i, mo in enumerate(mos):
            # Add manufacturing order content
            elements.extend(self.create_mo_elements(mo))

            # Add a page break between orders, except for the last one
            if i < len(mos) - 1:
                elements.append(PageBreak())

        # Build the PDF
        doc.build(elements)

        # Get the value of the BytesIO buffer
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def create_mo_elements(self, mo) -> List:
        """Create PDF elements for a single manufacturing order"""
        elements = []

        try:
            # Create header table with barcode, MO code, and date
            header_data = [[
                BarCode128(mo.code, width=2 * inch, height=0.5 * inch),
                Paragraph(mo.code, self.code_style),
                Paragraph(DateFormatter.format_date(mo.start_date), self.date_style)
            ]]

            header_table = Table(
                header_data,
                colWidths=[2.2 * inch, 2.2 * inch, 2.2 * inch],
                rowHeights=[0.6 * inch]
            )

            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA'))
            ]))

            elements.append(header_table)
            elements.append(Spacer(1, 15))

            # Create main information table
            row1_col1 = Paragraph(f"<b>{mo.item_code}</b><br/>{mo.item_title}", self.cell_style)
            row1_col2 = Paragraph(str(mo.target_lots[0].code) if mo.target_lots else "N/A", self.cell_style)
            row1_col3 = Paragraph(f"<b>Target Quantity:</b><br/>{mo.quantity} {mo.unit}", self.cell_style)

            row2_col1 = Paragraph(str(mo.target_lots[0].location) if mo.target_lots else "N/A", self.cell_style)
            row2_col2 = BarCode128(
                mo.target_lots[0].code if mo.target_lots else "N/A",
                width=1.8 * inch,
                height=0.4 * inch
            ) if mo.target_lots else Paragraph("N/A", self.cell_style)
            row2_col3 = Paragraph(
                f"<b>Actual Qty:</b> ____________<br/><b>Operator:</b> ____________",
                self.cell_style
            )

            info_table_data = [
                [row1_col1, row1_col2, row1_col3],
                [row2_col1, row2_col2, row2_col3]
            ]

            info_table = Table(
                info_table_data,
                colWidths=[2.2 * inch, 2.2 * inch, 2.2 * inch],
                rowHeights=[0.6 * inch, 0.6 * inch]
            )

            info_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFFFF'))
            ]))

            elements.append(info_table)
            elements.append(Spacer(1, 15))

            # Add parts table if parts exist
            if mo.parts:
                parts_table = self.create_parts_table(mo.parts)
                elements.append(parts_table)
                elements.append(Spacer(1, 15))

            # Add notes table if notes exist
            if mo.notes:
                elements.append(Paragraph("Notes", self.subtitle_style))
                notes_data = [["Note ID", "Author", "Text"]]
                for note in mo.notes:
                    notes_data.append([
                        str(note.note_id),
                        str(note.author),
                        str(note.text)
                    ])

                notes_table = Table(
                    notes_data,
                    colWidths=[0.8 * inch, 1.3 * inch, 4.5 * inch]
                )

                notes_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
                    ('PADDING', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('ALIGN', (0, 1), (-1, -1), 'LEFT')
                ]))
                elements.append(notes_table)

        except Exception as e:
            logging.error(f"Error creating PDF elements: {str(e)}")
            elements.append(Paragraph(f"Error creating PDF elements: {str(e)}", self.cell_style))

        return elements

    def create_parts_table(self, parts) -> Table:
        """Create a formatted table for parts information"""
        headers = ['Item', 'Location', 'Lot', 'Needed', 'Picked', 'Zeroed']
        table_data = [headers]
        row_count = 0
        spans = []
        item_end_rows = []

        for part in parts:
            start_row = row_count + 1

            for lot in part.lots:
                row = []

                # Add item information only for first lot in part
                if lot == part.lots[0]:
                    item_text = (
                        f"<b>{str(lot.item_code or 'N/A')}</b><br/>"
                        f"{str(lot.item_title or 'N/A')}"
                    )
                    row.append(Paragraph(item_text, self.item_style))
                else:
                    row.append('')

                # Safe handling of numeric calculations
                try:
                    percentage_of_uom = 0
                    percentage_value = 0
                    if (lot.unit_conversion_rate and
                        isinstance(lot.unit_conversion_rate, (int, float)) and
                        lot.unit_conversion_rate != 0):

                        booked_value = float(lot.booked or 0)
                        percentage_of_uom = booked_value / float(lot.unit_conversion_rate)
                        percentage_value = percentage_of_uom * 100
                except (ValueError, TypeError, ZeroDivisionError):
                    percentage_of_uom = 0
                    percentage_value = 0

                # Format the needed column with percentage
                needed_text = f"{str(lot.booked or 0)} {str(lot.unit or '')}"

                # Add vendor UOM information if applicable
                if lot.vendor_uom and percentage_value >= 5:
                    if percentage_value > 100:
                        rounded_value = round(percentage_of_uom * 10) / 10
                        display_value = int(rounded_value) if rounded_value.is_integer() else rounded_value
                        needed_text += f"<br/>({display_value} {str(lot.vendor_uom)})"
                    else:
                        rounded_percentage = round(percentage_value / 10) * 10
                        needed_text += f"<br/>({rounded_percentage}% of {str(lot.vendor_uom)})"

                # Add remaining columns
                row.extend([
                    Paragraph(str(lot.location or 'N/A'), self.cell_style),
                    KeepInFrame(
                        maxWidth=2 * inch,
                        maxHeight=0.9 * inch,
                        content=[
                            # Amin - temporary measure to remove lot code and barcode
                            # Paragraph(f"<b>{str(lot.code or 'N/A')}</b>", self.cell_style),
                            # Spacer(1, 4),
                            # BarCode128(str(lot.code or ''), width=1.5 * inch, height=0.3 * inch)
                            Paragraph("________", self.cell_style)
                        ],
                        mode='shrink'
                    ),
                    # Amin - temporary measure to remove needed qty
                    # Paragraph(needed_text, self.cell_style),
                    Paragraph("N/A", self.cell_style),
                    Paragraph("________", self.cell_style),
                    Checkbox(size=12)
                ])
                table_data.append(row)
                row_count += 1

            # Add placeholder row for additional entries
            placeholder_row = ['']
            placeholder_cells = [
                Paragraph("________", self.cell_style),
                Paragraph("________", self.cell_style),
                Paragraph("________", self.cell_style),
                Paragraph("________", self.cell_style),
                Checkbox(size=12)
            ]
            placeholder_row.extend(placeholder_cells)
            table_data.append(placeholder_row)
            row_count += 1

            if len(part.lots) >= 1:
                spans.append(('SPAN', (0, start_row), (0, row_count)))

            item_end_rows.append(row_count)

        # Create table with appropriate column widths
        table = Table(
            table_data,
            colWidths=[1.8 * inch, 1 * inch, 1.8 * inch, 1.3 * inch, 0.8 * inch, 0.7 * inch],
            rowHeights=[0.35 * inch] + [0.9 * inch] * (len(table_data) - 1)
        )

        # Apply table styles
        style = [
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            # Grid styling
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            # Content alignment
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]

        # Apply spans for item columns first
        style.extend(spans)

        # Clean up grid lines in spanned cells, but preserve separator positions
        separator_rows = set(item_end_rows[:-1])  # Convert to set for O(1) lookup
        for span in spans:
            if span[0] == 'SPAN':
                start_row = span[1][1]
                end_row = span[2][1]
                for row in range(start_row, end_row):
                    # Only remove grid lines if this isn't a separator row
                    if row not in separator_rows:
                        style.append(('LINEABOVE', (0, row), (0, row), 0, colors.white))
                        style.append(('LINEBELOW', (0, row), (0, row), 0, colors.white))

        # Add enhanced separators between item groups
        for end_row in item_end_rows[:-1]:
            # Add extra padding above and below separator
            style.append(('BOTTOMPADDING', (0, end_row), (-1, end_row), 12))
            style.append(('TOPPADDING', (0, end_row + 1), (-1, end_row + 1), 12))

            # Add thicker, darker separator line across all columns
            style.append(('LINEBELOW', (0, end_row), (-1, end_row), 3, colors.HexColor('#2C3E50')))

            # Add light background to the separator row
            style.append(('BACKGROUND', (0, end_row), (-1, end_row), colors.HexColor('#F8F9FA')))

        table.setStyle(TableStyle(style))
        return table
