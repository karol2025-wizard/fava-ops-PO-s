# component_tree_pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Flowable
from reportlab.graphics.barcode import code128
from io import BytesIO
from datetime import datetime
import pandas as pd


class DateFormatter:
    """Utility class for date formatting"""

    @staticmethod
    def format_date(date_value):
        """Convert date value to readable format"""
        if not date_value:
            return "Not specified"

        try:
            if isinstance(date_value, (datetime, pd.Timestamp)):
                return date_value.strftime('%a %b %d %Y')
            elif isinstance(date_value, str):
                try:
                    # First try parsing as a datetime string
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').strftime('%a %b %d %Y')
                except ValueError:
                    try:
                        # Try parsing as a date string (YYYY-MM-DD)
                        return datetime.strptime(date_value, '%Y-%m-%d').strftime('%a %b %d %Y')
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
            return f"Date Error: {str(e)}"


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


class EnhancedComponentTreePDFGenerator:
    """Enhanced class for generating PDF reports for Component Tree Manufacturing Orders with components"""

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

        # Smaller font style for related manufacturing orders
        self.small_item_style = ParagraphStyle(
            'SmallItemCell',
            parent=self.styles['Normal'],
            fontSize=8,  # Smaller font size
            leading=10,  # Reduced leading for tighter line spacing
            textColor=colors.HexColor('#2C3E50')
        )

        # Component style for indented components
        self.component_style = ParagraphStyle(
            'ComponentCell',
            parent=self.styles['Normal'],
            fontSize=9,  # Slightly smaller font size
            leading=12,  # Reduced leading for tighter line spacing
            textColor=colors.HexColor('#34495E')
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

        # Code style for lot numbers
        self.code_style = ParagraphStyle(
            'CustomCode',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=1,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )

        # Description style for indented items
        self.description_style = ParagraphStyle(
            'DescriptionCell',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            leftIndent=0,
            textColor=colors.HexColor('#2C3E50')
        )

    def create_component_tree_pdf(self, manufacturing_orders, bom_tree, target_date, lot_code_map=None):
        """Generate a PDF report for component tree manufacturing orders

        Args:
            manufacturing_orders (list): List of created manufacturing order data
            bom_tree (list): The component tree data
            target_date (datetime): Date selected by the user
            lot_code_map (dict, optional): Dictionary mapping lot_id to lot_code

        Returns:
            bytes: PDF file content as bytes
        """
        buffer = BytesIO()

        # Create the PDF document in landscape orientation with reduced margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),  # Changed to landscape orientation
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
            title="Component Tree Production Summary"
        )

        elements = []

        # Create header with title and date
        header_data = [[
            Paragraph("Component Tree Production Summary", self.title_style),
            Paragraph(DateFormatter.format_date(target_date), self.date_style)
        ]]

        header_table = Table(
            header_data,
            colWidths=[5.0 * inch, 5.0 * inch],
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

        # Add production summary subtitle
        elements.append(Paragraph("Production Summary", self.subtitle_style))

        if lot_code_map is None:
            lot_code_map = {}

        # Create table with specified columns
        table_data = [
            ["Lot Code", "Item", "Quantity", "Components", "Source Lots","Start Time", "End Time", "Staff Names", "Related MOs"]
        ]

        # Function to get direct components of an item
        def get_direct_components(item, bom_tree):
            item_code = item.get('item_code', '')
            article_id = item.get('article_id', None)

            # Find direct components from the BOM tree
            direct_components = [
                component for component in bom_tree
                if any(
                    (prev_comp.get('item_code', '') == item_code or prev_comp.get('article_id', '') == article_id)
                    and prev_comp.get('level', 0) + 1 == component.get('level', 0)
                    for prev_comp in bom_tree
                )
            ]

            return direct_components

        # Process each manufacturing order and match with bom_tree item
        for mo in manufacturing_orders:
            try:
                # Find the corresponding item in bom_tree
                article_id = mo.get('article_id', None)
                item = next((item for item in bom_tree if item.get('article_id') == article_id), None)

                if not item:
                    continue

                # Get target lot ID
                target_lot_id = None
                if "target_lots" in mo and mo["target_lots"]:
                    for lot in mo["target_lots"]:
                        if "lot_id" in lot:
                            target_lot_id = lot["lot_id"]
                            break

                # Format target lot code
                target_lot_code = lot_code_map.get(target_lot_id, 'N/A') if target_lot_id else 'N/A'

                # Create barcode and code text for lot code cell
                if target_lot_code != 'N/A':
                    # Create a table to help with centering
                    barcode_table = Table(
                        [
                            [Paragraph(target_lot_code, self.code_style)],
                            [Spacer(1, 4)],
                            [BarCode128(target_lot_code, width=1.6 * inch, height=0.4 * inch)]
                        ],
                        colWidths=[1.8 * inch],  # Slightly smaller than cell width to account for padding
                        rowHeights=[0.15 * inch, 0.05 * inch, 0.4 * inch]
                    )
                    barcode_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))

                    lot_code_cell = barcode_table
                else:
                    lot_code_cell = Paragraph(target_lot_code, self.cell_style)

                # Format related manufacturing orders
                mo_info = ""
                if item.get("manufacturing_orders"):
                    mo_details = []
                    for related_mo in item["manufacturing_orders"]:
                        mo_details.append(
                            f"{related_mo['code']} | {related_mo['status_text']} | {related_mo['formatted_start_date']}"
                        )
                    mo_info = "<br/>".join(mo_details)

                # Create indent based on level
                level = item.get("level", 0)
                indent = "&nbsp;" * (level * 4)  # HTML spaces for indentation

                # Create indented style for this item
                indented_style = ParagraphStyle(
                    f'Level{level}',
                    parent=self.description_style,
                    leftIndent=level * 12  # 12 points per level
                )

                # Add manufacturing order data
                row = [
                    # Target Lot Code with Barcode (as a complete table)
                    lot_code_cell,

                    # Target Lot Item Code + Title with indent
                    Paragraph(f"{indent}{mo.get('item_code', 'N/A')}<br/>{indent}{mo.get('item_title', 'N/A')}",
                              indented_style),

                    # Quantity
                    Paragraph(f"{mo.get('quantity', '')} {mo.get('unit', '')}", self.cell_style),

                    # Source Lots - empty as requested
                    Paragraph("", self.cell_style),

                    # Start Time - empty as requested
                    Paragraph("", self.cell_style),

                    # End Time - empty as requested
                    Paragraph("", self.cell_style),

                    # Staff Names - empty as requested
                    Paragraph("", self.cell_style),

                    # Related Manufacturing Orders - with smaller font
                    Paragraph(mo_info, self.small_item_style)
                ]

                table_data.append(row)

                # Get the direct components for this item
                components = get_direct_components(item, bom_tree)

                # Add each component as a separate row
                for component in components:
                    component_level = component.get("level", 0)
                    component_indent = "&nbsp;" * (component_level * 4)

                    component_style = ParagraphStyle(
                        f'Level{component_level}',
                        parent=self.description_style,
                        leftIndent=component_level * 12
                    )

                    component_row = [
                        # Target Lot Code - empty for components
                        Paragraph("", self.cell_style),

                        # Component Item Code + Title with indent
                        Paragraph(f"{component_indent}{component.get('item_code', 'N/A')}<br/>{component_indent}{component.get('title', 'N/A')}",
                                 component_style),

                        # Quantity
                        Paragraph(f"{component.get('quantity', '')}", self.cell_style),

                        # Source Lots - empty
                        Paragraph("", self.cell_style),

                        # Start Time - empty
                        Paragraph("", self.cell_style),

                        # End Time - empty
                        Paragraph("", self.cell_style),

                        # Staff Names - empty
                        Paragraph("", self.cell_style),

                        # Related Manufacturing Orders - empty for components
                        Paragraph("", self.cell_style)
                    ]

                    table_data.append(component_row)

            except Exception as e:
                # Skip this row if there's an error
                continue

        # Calculate column widths with Target Lot Item at half width and other adjustments
        column_widths = [
            1.7 * inch,     # Target Lot Code
            1.6 * inch,     # Target Lot Item
            0.8 * inch,     # Quantity
            0.9 * inch,     # Source Lots
            0.8 * inch,     # Start Time
            0.8 * inch,     # End Time
            0.8 * inch,     # Staff Names
            2.2 * inch      # Related Manufacturing Orders
        ]

        # Create table with appropriate column widths
        parts_table = Table(
            table_data,
            colWidths=column_widths,
            rowHeights=[0.35 * inch] + [0.6 * inch] * (len(table_data) - 1)  # Standard height for all content rows
        )

        # Apply table styles
        parts_table.setStyle(TableStyle([
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
            ('ALIGN', (2, 1), (6, -1), 'CENTER'),  # Center columns 2-6
            # Row styling - alternating colors for better readability
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8F9FA')]),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(parts_table)

        # Build the PDF
        doc.build(elements)

        # Get the value of the BytesIO buffer
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes