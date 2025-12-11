# pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Flowable, KeepInFrame
from reportlab.graphics.barcode import code128
from io import BytesIO
from datetime import datetime
from typing import Union, List, Optional, Tuple
import logging
import math
import re


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


class HatchedCell(Flowable):
    """A custom Flowable for creating hatched cells to indicate 'do not fill in'"""

    def __init__(self, width, height, text="DO NOT WRITE", text_color=colors.HexColor('#777777'),
                 bg_color=colors.HexColor('#DDDDDD'), line_color=colors.darkgrey):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.text = text
        self.text_color = text_color
        self.bg_color = bg_color
        self.line_color = line_color

    def wrap(self, availWidth, availHeight):
        """Returns the size this flowable will take up"""
        return self.width, self.height

    def draw(self):
        """Draw the hatched cell with text"""
        # Save canvas state
        self.canv.saveState()

        # Draw background
        self.canv.setFillColor(self.bg_color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)

        # Draw diagonal lines (hatching pattern)
        self.canv.setStrokeColor(self.line_color)
        self.canv.setLineWidth(0.5)

        # Draw diagonal lines from top-left to bottom-right
        line_spacing = 10  # space between lines in points
        num_lines = int((self.width + self.height) / line_spacing) + 2

        for i in range(num_lines):
            start_x = i * line_spacing
            start_y = self.height

            end_x = 0
            end_y = self.height - i * line_spacing

            if start_x > self.width:
                start_x = self.width
                start_y = self.height - (start_x - self.width)

            if end_y < 0:
                end_y = 0
                end_x = i * line_spacing - self.height

            self.canv.line(start_x, start_y, end_x, end_y)

        # Draw diagonal lines from top-right to bottom-left
        for i in range(num_lines):
            start_x = self.width - i * line_spacing
            start_y = self.height

            end_x = self.width
            end_y = self.height - i * line_spacing

            if start_x < 0:
                start_x = 0
                start_y = self.height - (0 - start_x)

            if end_y < 0:
                end_y = 0
                end_x = self.width - (i * line_spacing - self.height)

            self.canv.line(start_x, start_y, end_x, end_y)

        # Draw text
        if self.text:
            self.canv.setFillColor(self.text_color)
            self.canv.setFont("Helvetica-Bold", 10)

            # Center the text
            text_width = self.canv.stringWidth(self.text, "Helvetica-Bold", 10)
            x = (self.width - text_width) / 2
            y = (self.height - 10) / 2  # Approximation for centering vertically

            self.canv.drawString(x, y, self.text)

        # Restore canvas state
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
            leading=12,  # Reduced leading for single line items
            textColor=colors.HexColor('#2C3E50')
        )

        # Single line item style for parts table
        self.single_line_item_style = ParagraphStyle(
            'SingleLineItemCell',
            parent=self.styles['Normal'],
            fontSize=9,  # Slightly smaller font size
            leading=10,  # Minimal leading for single line display
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

        # Notice style for bag packaging instructions
        self.notice_style = ParagraphStyle(
            'NoticeStyle',
            parent=self.styles['Normal'],
            fontSize=13,
            alignment=1,
            spaceAfter=15,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#E74C3C')  # Red color for emphasis
        )

    def extract_secondary_uom(self, uom: str) -> Optional[str]:
        """
        Extract secondary UOM from formats like "Bag (4 kg)"
        Returns the value inside parentheses if found, otherwise None
        """
        if not uom:
            return None

        # Use regex to find content within parentheses
        match = re.search(r'\((.*?)\)', uom)
        if match:
            return match.group(1)
        return None

    def is_container_uom(self, uom: str) -> bool:
        """
        Check if UOM starts with any of the container types:
        'bag', 'tray', 'container', 'bucket', or 'pail' (case insensitive)
        """
        if not uom:
            return False
        container_types = ['bag', 'tray', 'container', 'bucket', 'pail']
        return any(uom.lower().startswith(container_type) for container_type in container_types)

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
            # Create header table with barcode and date
            header_data = [[
                # BarCode128(mo.code, width=2 * inch, height=0.5 * inch),
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

            # Get target UOM and check if it's a container type
            target_uom = mo.unit
            is_container = self.is_container_uom(target_uom)
            secondary_uom = self.extract_secondary_uom(target_uom) if is_container else None

            # Create main information table
            row1_col1 = Paragraph(f"<b>{mo.item_code}</b><br/>{mo.item_title}", self.cell_style)

            # Fix the lot code and barcode structure
            if mo.target_lots:
                lot_code = str(mo.target_lots[0].code)
                # Create a table to help with centering
                inner_table = Table(
                    [
                        [Paragraph(lot_code, self.code_style)],
                        [Spacer(1, 4)],
                        [BarCode128(lot_code, width=1.8 * inch, height=0.4 * inch)]
                    ],
                    colWidths=[2.1 * inch],  # Slightly smaller than cell width to account for padding
                    rowHeights=[0.15 * inch, 0.05 * inch, 0.4 * inch]
                )
                inner_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))

                row1_col2 = inner_table
            else:
                row1_col2 = Paragraph("N/A", self.cell_style)

            row1_col3 = Paragraph(f"<b>Target Quantity:</b><br/>{mo.quantity} {mo.unit}", self.cell_style)

            # Change 1: Remove location from row2_col1 and leave it blank
            row2_col1 = Paragraph("", self.cell_style)

            row2_col2 = Paragraph(
                "<b>Name:</b> ____________",
                self.cell_style
            )

            # Update row2_col3 to include the target UOM
            row2_col3 = Paragraph(
                f"<b>Qty Final:</b> ______{target_uom}",
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

            # Add the special notice for container packaging if applicable
            if is_container and secondary_uom:
                # Extract the container type from the UOM (e.g., "Bag" from "Bag (4 kg)")
                container_type = target_uom.split()[0].title()
                notice_text = f"NOTICE! PACK IN {container_type.upper()}S OF {secondary_uom}"
                elements.append(Paragraph(notice_text, self.notice_style))
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
        headers = ['Item', 'Location', 'Lot']
        table_data = [headers]

        # Define which group titles should have hatched cells
        no_write_groups = ["Spices", "Pantry", "Oils", "Grains", "Packaging", "Nuts", "Dairy", "Veges", "Breads",
                           "Composed Veges", "Breads", "Dips", "Desserts", "Salads", "Sauces", "Packaging",
                           "Non-consumables", "Appetizers"]

        for part in parts:
            # Get the first lot's location or 'N/A' if no lots
            location = str(part.lots[0].location if part.lots else 'N/A')

            # Create a single line item text by combining code and title with a dash
            item_code = str(part.item_code if part.item_code else 'N/A')
            item_title = str(part.item_title if part.item_title else 'N/A')

            # Combine code and title on a single line with a dash separator
            item_text = f"<b>{item_code}</b> - {item_title}"

            # Check if this part belongs to a no-write group
            should_hatch = False
            if part.lots and hasattr(part.lots[0], 'group_title'):
                group_title = part.lots[0].group_title
                should_hatch = group_title in no_write_groups

            # Create the lot cell content
            if should_hatch:
                # Use our custom HatchedCell for no-write groups
                lot_cell = HatchedCell(
                    width=2.7 * inch,  # Slightly less than column width to account for padding
                    height=0.2 * inch,  # Reduced height for the cell
                    text="DO NOT WRITE"
                )
            else:
                # Normal empty cell for other groups
                lot_cell = Paragraph("", self.cell_style)

            # Create single row for the part
            row = [
                Paragraph(item_text, self.single_line_item_style),  # Use the new single line style
                Paragraph(location, self.cell_style),
                lot_cell
            ]
            table_data.append(row)

        # Create table with appropriate column widths
        # Slightly increase row height to prevent crowding after moving to single-line format
        table = Table(
            table_data,
            colWidths=[2.5 * inch, 1.2 * inch, 2.8 * inch],
            rowHeights=[0.35 * inch] + [0.25 * inch] * (len(table_data) - 1)  # Slightly increased from 0.225 * inch
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
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]

        table.setStyle(TableStyle(style))
        return table