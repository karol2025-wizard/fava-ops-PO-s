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
    """Format order details for display

    Args:
        order: Dictionary containing order information

    Returns:
        Formatted string with order details
    """
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


def format_outlier_description(value: float, historical_mean: float, weekday_name: str) -> str:
    """Format outlier description with deviation from historical mean

    Args:
        value: Current value
        historical_mean: Historical mean value
        weekday_name: Name of the weekday for context

    Returns:
        Formatted description string
    """
    deviation_pct = ((value - historical_mean) / historical_mean) * 100
    direction = "above" if deviation_pct > 0 else "below"

    return (f"{format_currency(value)} "
            f"({format_percentage(abs(deviation_pct))} {direction} average for {weekday_name}s)")


def display_outliers_section(title: str, outliers: List[Dict], weekday_name: str,
                             value_key: str, name_key: str = None,
                             show_details: bool = False) -> None:
    """Display a section of outliers with consistent formatting

    Args:
        title: Section title
        outliers: List of outlier dictionaries
        weekday_name: Name of the weekday for context
        value_key: Key for the value in outlier dictionary
        name_key: Optional key for the name in outlier dictionary
        show_details: Whether to show detailed order information
    """
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
                f"(:green[{format_percentage(outlier['deviation_percentage'])}] above average for {weekday_name}s)"
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
                f"(:red[{format_percentage(abs(outlier['deviation_percentage']))}] below average for {weekday_name}s)"
            )

            if show_details:
                with st.expander("Click to see order details"):
                    _display_order_details(outlier)


def display_daily_summary(summary: Dict, historical_summary: Dict, weekday_name: str) -> None:
    """Display daily summary with comparisons to historical averages

    Args:
        summary: Dictionary of current day metrics
        historical_summary: Dictionary of historical average metrics
        weekday_name: Name of the weekday for context
    """
    st.subheader("Daily Performance Summary")

    metrics = [
        ("Total Sales", float(summary.get('total_sales', 0)),
         float(historical_summary.get('avg_total_sales', 0))),

        ("Total Tips", float(summary.get('total_tips', 0)),
         float(historical_summary.get('avg_total_tips', 0))),

        ("Order Level Discounts", float(summary.get('order_discounts', 0)),
         float(historical_summary.get('avg_order_discounts', 0))),

        ("Item Level Discounts", float(summary.get('item_discounts', 0)),
         float(historical_summary.get('avg_item_discounts', 0))),

        ("Total Modifications", float(summary.get('total_mods', 0)),
         float(historical_summary.get('avg_total_mods', 0)))
    ]

    for metric_name, current_value, historical_avg in metrics:
        if historical_avg > 0:
            deviation_pct = ((current_value - historical_avg) / historical_avg) * 100
            direction = ":green" if deviation_pct > 0 else ":red"

            st.markdown(
                f"**{metric_name}:** {format_currency(current_value)} "
                f"({direction}[{format_percentage(abs(deviation_pct))}] "
                f"{'above' if deviation_pct > 0 else 'below'} average for {weekday_name}s)"
            )


def _display_order_details(order: Dict) -> None:
    """Helper function to display detailed order information

    Args:
        order: Dictionary containing order information
    """
    st.markdown("**Delivery Information**")
    st.markdown(f"• Method: {order['delivery_method']}")
    st.markdown(f"• Platform: {order['delivery_platform']}")
    st.markdown(f"• Order Total: {format_currency(order['total'])}")
    st.markdown(f"• Tip Amount: {format_currency(order['tip_amount'])} ({format_percentage(order['tip_amount']/order['total']*100)} of total)")

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