# analysis/formatters.py
from typing import Dict, List
from datetime import datetime
import streamlit as st
from clover_sales_analysis.models import OrderItem


def format_currency(amount: float) -> str:
    """Format a number as currency"""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format a number as percentage"""
    return f"{value:.1f}%"


def format_order_details(order: Dict) -> str:
    """Format order details for display"""
    details = [
        f"Delivery: {order['delivery_method']} ({order['delivery_platform']})",
        f"Tip: {format_currency(order['tip_amount'])}",
        "\nItems ordered:",
    ]

    for item in order['items']:
        if isinstance(item, OrderItem):
            # Handle OrderItem objects
            unit_price = float(item.total_price) / item.quantity
            details.append(
                f"• {item.clover_name}: {item.quantity} × "
                f"{format_currency(unit_price)} = {format_currency(float(item.total_price))}"
            )
        else:
            # Handle dictionary items
            unit_price = item['total_price'] / item['quantity']
            details.append(
                f"• {item['clover_name']}: {item['quantity']} × "
                f"{format_currency(unit_price)} = {format_currency(item['total_price'])}"
            )

    return "\n".join(details)


def format_outlier_description(value: float, historical_mean: float) -> str:
    """Format outlier description with deviation from historical mean"""
    deviation_pct = ((value - historical_mean) / historical_mean) * 100
    direction = "above" if deviation_pct > 0 else "below"
    return f"{format_currency(value)} ({format_percentage(abs(deviation_pct))} {direction} historical average)"


def display_outliers_section(title: str, outliers: List[Dict], period: str,
                           value_key: str, name_key: str = None,
                           show_details: bool = False) -> None:
    """Display a section of outliers with consistent formatting"""
    if not outliers:
        return

    st.subheader(title)

    # Split into above and below average
    above_avg = [o for o in outliers if o['deviation_percentage'] > 0]
    below_avg = [o for o in outliers if o['deviation_percentage'] <= 0]

    # Display above average
    if above_avg:
        st.markdown("##### Above Average")
        for outlier in sorted(above_avg, key=lambda x: x['deviation_percentage'], reverse=True):
            label = outlier['order_id'] if name_key is None else outlier[name_key]
            value = outlier[value_key]

            # Handle special cases
            if title == "Unusual Tips":
                display_text = (
                    f"{label}: {format_currency(value)} "
                    f"({format_percentage(outlier['tip_percentage'])} of total)"
                )
            elif title == "Unusual Order Totals":
                display_text = f"{label} ({outlier['delivery_platform']}): {format_currency(value)}"
            else:
                display_text = f"{label}: {format_currency(value)}"

            st.markdown(
                f"{display_text} "
                f"(:green[{format_percentage(outlier['deviation_percentage'])}] above historical average)"
            )

            if show_details:
                with st.expander("Click to see order details"):
                    _display_order_details(outlier)

    # Display below average
    if below_avg:
        st.markdown("##### Below Average")
        for outlier in sorted(below_avg, key=lambda x: x['deviation_percentage']):
            label = outlier['order_id'] if name_key is None else outlier[name_key]
            value = outlier[value_key]

            # Handle special cases
            if title == "Unusual Order Totals":
                display_text = f"{label} ({outlier['delivery_platform']}): {format_currency(value)}"
            else:
                display_text = f"{label}: {format_currency(value)}"

            st.markdown(
                f"{display_text} "
                f"(:red[{format_percentage(abs(outlier['deviation_percentage']))}] below historical average)"
            )

            if show_details:
                with st.expander("Click to see order details"):
                    _display_order_details(outlier)


def _display_order_details(order: Dict) -> None:
    """Helper function to display detailed order information"""
    st.markdown("**Delivery Information**")
    st.markdown(f"• Method: {order['delivery_method']}")
    st.markdown(f"• Platform: {order['delivery_platform']}")
    st.markdown(f"• Tip Amount: {format_currency(order['tip_amount'])}")

    st.markdown("\n**Items Ordered**")
    for item in order['items']:
        if isinstance(item, OrderItem):
            unit_price = float(item.total_price) / item.quantity
            total_price = float(item.total_price)
            name = item.clover_name
            quantity = item.quantity
        else:
            unit_price = item['total_price'] / item['quantity']
            total_price = item['total_price']
            name = item['clover_name']
            quantity = item['quantity']

        st.markdown(
            f"• {name}\n"
            f"    - Quantity: {quantity}\n"
            f"    - Price per unit: {format_currency(unit_price)}\n"
            f"    - Total: {format_currency(total_price)}"
        )