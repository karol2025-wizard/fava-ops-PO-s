"""
Production Summary & Print Module

This module generates production summaries after successful MRPeasy updates
and provides printing functionality.

Requirements:
- Generate production summary after successful MRPeasy update
- Allow printing of summary
- Summary must include: MO Number, Item, Lot Code, Produced Quantity, Date & Time
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

logger = logging.getLogger(__name__)


class ProductionSummary:
    """Generate and print production summaries"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the summary"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Normal style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6
        )
        
        # Label style (for key-value pairs)
        self.label_style = ParagraphStyle(
            'CustomLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=2
        )
        
        # Value style (for key-value pairs)
        self.value_style = ParagraphStyle(
            'CustomValue',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#000000'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
    
    def generate_summary_data(
        self,
        mo_number: str,
        item_code: str,
        item_title: str,
        lot_code: str,
        produced_quantity: float,
        produced_unit: str,
        expected_output: float = None,
        expected_unit: str = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate summary data dictionary.
        
        Args:
            mo_number: MO Number
            item_code: Item code
            item_title: Item title/name
            lot_code: Lot Code
            produced_quantity: Produced quantity
            produced_unit: Unit of measure for produced quantity
            expected_output: Expected output quantity (optional)
            expected_unit: Unit of measure for expected output (optional)
            timestamp: Timestamp of production (defaults to now)
        
        Returns:
            Dict with summary data
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        summary_data = {
            'mo_number': mo_number,
            'item_code': item_code,
            'item_title': item_title,
            'lot_code': lot_code,
            'produced_quantity': produced_quantity,
            'produced_unit': produced_unit,
            'expected_output': expected_output,
            'expected_unit': expected_unit,
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M:%S'),
            'datetime': timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return summary_data
    
    def create_summary_pdf(self, summary_data: Dict[str, Any]) -> BytesIO:
        """
        Create a PDF summary document.
        
        Args:
            summary_data: Dictionary with summary data from generate_summary_data()
        
        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        # Build PDF content
        story = []
        
        # Title
        title = Paragraph("Production Summary", self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Production Information Section
        story.append(Paragraph("Production Information", self.header_style))
        
        # Create information table
        info_data = [
            ['MO Number:', summary_data['mo_number']],
            ['Item Code:', summary_data['item_code']],
            ['Item:', summary_data['item_title']],
            ['Lot Code:', summary_data['lot_code']],
        ]
        
        # Add estimated quantity (for reference) if available - BEFORE actual quantity
        if summary_data.get('expected_output') is not None:
            expected_str = f"{summary_data['expected_output']} {summary_data.get('expected_unit', '')}"
            info_data.append(['Estimated Quantity (for reference):', expected_str])
        
        # Add actual produced quantity (highlighted) - AFTER estimated
        actual_qty_str = f"{summary_data['produced_quantity']} {summary_data['produced_unit']}"
        info_data.append(['Actual Produced Quantity:', actual_qty_str])
        
        info_data.extend([
            ['Date:', summary_data['date']],
            ['Time:', summary_data['time']]
        ])
        
        # Find the row index for actual produced quantity (for highlighting)
        actual_qty_row = len(info_data) - 3  # Row index (0-based) for actual produced quantity
        
        info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            # Highlight actual produced quantity row
            ('BACKGROUND', (0, actual_qty_row), (-1, actual_qty_row), colors.HexColor('#e8f5e9')),  # Light green background
            ('FONTNAME', (1, actual_qty_row), (1, actual_qty_row), 'Helvetica-Bold'),  # Bold actual quantity
            ('FONTSIZE', (1, actual_qty_row), (1, actual_qty_row), 12),  # Larger font for actual quantity
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer_text = f"Generated on {summary_data['datetime']}"
        footer = Paragraph(footer_text, self.label_style)
        story.append(footer)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def generate_summary_text(self, summary_data: Dict[str, Any]) -> str:
        """
        Generate a text summary (for display or logging).
        
        Args:
            summary_data: Dictionary with summary data
        
        Returns:
            Formatted text summary
        """
        text = f"""
PRODUCTION SUMMARY
==================

MO Number: {summary_data['mo_number']}
Item Code: {summary_data['item_code']}
Item: {summary_data['item_title']}
Lot Code: {summary_data['lot_code']}
"""
        
        if summary_data.get('expected_output') is not None:
            text += f"Estimated Quantity (for reference): {summary_data['expected_output']} {summary_data.get('expected_unit', '')}\n"
        
        text += f"Actual Produced Quantity: {summary_data['produced_quantity']} {summary_data['produced_unit']}\n"
        
        text += f"""
Date: {summary_data['date']}
Time: {summary_data['time']}
"""
        
        return text.strip()

