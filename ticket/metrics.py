from decimal import Decimal
from django.db.models import Count, Max

from ticket import models as ticket_models
from ticket import constants as ticket_constants


def get_most_cancelled_date():
    result = (
        ticket_models.Ticket.objects.filter(
            order__state=ticket_constants.CANCELLED_STATE
        )
        .values("ticket_type__event__event_date")
        .annotate(cancelled_quantity=Count("id"))
        .order_by("cancelled_quantity")
    )

    return result.last()


def number_of_orders_and_cancellation_rate(event_id):
    total_orders = ticket_models.Order.objects.filter(
        ticket_type__event__id=event_id
    ).count()

    cancelled_orders = ticket_models.Order.objects.filter(
        ticket_type__event__id=event_id, state=ticket_constants.CANCELLED_STATE
    ).count()

    res = {
        "total": total_orders,
        "cancellation_rate_percentage": Decimal(
            round(cancelled_orders / total_orders * 100, 2)
        ),
    }
    return res
