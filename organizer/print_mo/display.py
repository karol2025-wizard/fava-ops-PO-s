import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Union
import logging
from enum import Enum

# Constants
class DisplayText(str, Enum):
    """Enum for display text strings"""
    NOT_SPECIFIED = "Not specified"
    NO_DATA = "N/A"

class TableHeaders(str, Enum):
    """Enum for table headers"""
    TARGET_LOTS = "Target Lots"
    PARTS = "Parts"
    NOTES = "Notes"

class DateFormatter:
    """Utility class for date formatting"""

    @staticmethod
    def format_date(date_value: Union[str, int, float, None]) -> str:
        """Convert date value to readable format"""
        if not date_value:
            return DisplayText.NOT_SPECIFIED

        try:
            if isinstance(date_value, str):
                try:
                    return datetime.fromisoformat(date_value).strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return date_value
            elif isinstance(date_value, (int, float)):
                # Convert seconds to milliseconds by multiplying by 1000
                return datetime.fromtimestamp(float(date_value)).strftime('%Y-%m-%d %H:%M:%S')
            return str(date_value)
        except Exception as e:
            logging.error(f"Error formatting date: {str(e)}")
            raise Exception(f"Error formatting date: {str(e)}")

class MODisplay:
    """Display component for Manufacturing Order data"""

    @staticmethod
    def display_basic_info(mo) -> None:
        """Display basic manufacturing order information"""
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="mo_code", value=mo.code)
                st.metric(label="mo_start_date", value=DateFormatter.format_date(mo.start_date))
                st.metric(label="mo_target_item_code", value=mo.item_code)

            with col2:
                st.metric(label="mo_target_item_title", value=mo.item_title)
                st.metric(label="mo_target_item_quantity", value=str(mo.quantity))
                st.metric(label="mo_target_item_uom", value=mo.unit)
        except Exception as e:
            logging.error(f"Error displaying basic info: {str(e)}")
            st.error("Error displaying basic information")

    @staticmethod
    def display_target_lots(target_lots: List) -> None:
        """Display target lots information"""
        if target_lots:
            st.subheader(TableHeaders.TARGET_LOTS)
            data = [{
                'mo_target_lot_lot_id': lot.lot_id,
                'mo_target_lot_code': lot.code,
                'mo_target_lot_location': lot.location or DisplayText.NO_DATA
            } for lot in target_lots]
            st.table(data)

    @staticmethod
    def display_parts(parts: List) -> None:
        """Display parts information"""
        if parts:
            st.subheader(TableHeaders.PARTS)
            all_lots = []
            for part in parts:
                for lot in part.lots:
                    all_lots.append({
                        'mo_parts_item_code': lot.item_code or DisplayText.NO_DATA,
                        'mo_parts_item_name': lot.item_title or DisplayText.NO_DATA,
                        'mo_parts_lot_lot_id': lot.lot_id,
                        'mo_parts_lot_code': lot.code,
                        'mo_parts_lot_booked': lot.booked,
                        'mo_parts_item_uom': lot.unit or DisplayText.NO_DATA,
                        'mo_parts_lot_location': lot.location or DisplayText.NO_DATA,
                        'mo_parts_lot_vendor_uom': lot.vendor_uom or DisplayText.NO_DATA,
                        'mo_parts_lot_vendor_id': lot.vendor_id or DisplayText.NO_DATA,
                        'mo_parts_lot_unit_conversion_rate': lot.unit_conversion_rate or DisplayText.NO_DATA,
                        'mo_parts_lot_percentage_of_vendor_uom': f"{lot.vendor_uom_percentage:.2f}" if lot.vendor_uom_percentage is not None else DisplayText.NO_DATA
                    })
            if all_lots:
                # Convert to DataFrame
                df = pd.DataFrame(all_lots)

                # Sort by item_code and item_name
                df = df.sort_values(['mo_parts_item_code', 'mo_parts_item_name'])

                # Group by item_code and item_name
                groups = df.groupby(['mo_parts_item_code', 'mo_parts_item_name'])

                # Process each group
                formatted_data = []
                for (item_code, item_name), group in groups:
                    # Add header row with item code and name
                    formatted_data.append({
                        'mo_parts_item_code': item_code,
                        'mo_parts_item_name': item_name,
                        'mo_parts_lot_lot_id': '',
                        'mo_parts_lot_code': '',
                        'mo_parts_lot_booked': '',
                        'mo_parts_item_uom': '',
                        'mo_parts_lot_location': '',
                        'mo_parts_lot_vendor_uom': '',
                        'mo_parts_lot_vendor_id': '',
                        'mo_parts_lot_unit_conversion_rate': '',
                        'mo_parts_lot_percentage_of_vendor_uom': ''
                    })

                    # Add detail rows without repeating item code and name
                    for _, row in group.iterrows():
                        formatted_data.append({
                            'mo_parts_item_code': '',
                            'mo_parts_item_name': '',
                            'mo_parts_lot_lot_id': row['mo_parts_lot_lot_id'],
                            'mo_parts_lot_code': row['mo_parts_lot_code'],
                            'mo_parts_lot_booked': row['mo_parts_lot_booked'],
                            'mo_parts_item_uom': row['mo_parts_item_uom'],
                            'mo_parts_lot_location': row['mo_parts_lot_location'],
                            'mo_parts_lot_vendor_uom': row['mo_parts_lot_vendor_uom'],
                            'mo_parts_lot_vendor_id': row['mo_parts_lot_vendor_id'],
                            'mo_parts_lot_unit_conversion_rate': row['mo_parts_lot_unit_conversion_rate'],
                            'mo_parts_lot_percentage_of_vendor_uom': row['mo_parts_lot_percentage_of_vendor_uom']
                        })

                    # Add a blank row between groups
                    formatted_data.append(dict.fromkeys(formatted_data[0].keys(), ''))

                # Display the formatted table
                st.table(formatted_data)

    @staticmethod
    def display_notes(notes: List) -> None:
        """Display notes information"""
        if notes:
            st.subheader(TableHeaders.NOTES)
            data = [{
                'mo_notes_note_id': note.note_id,
                'mo_notes_author': note.author,
                'mo_notes_text': note.text
            } for note in notes]
            st.table(data)

    @staticmethod
    def display_error(error_message: str) -> None:
        """Display error message"""
        st.error(error_message)

    @staticmethod
    def display_success(success_message: str) -> None:
        """Display success message"""
        st.success(success_message)

    @staticmethod
    def display_warning(warning_message: str) -> None:
        """Display warning message"""
        st.warning(warning_message)

    @staticmethod
    def display_info(info_message: str) -> None:
        """Display info message"""
        st.info(info_message)