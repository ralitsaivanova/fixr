from datetime import date
from decimal import Decimal

from django.test import TestCase
from django_dynamic_fixture import G

from ticket import metrics as ticket_metrics
from ticket import models as ticket_models
from ticket import constants as ticket_constants


class MetricTest(TestCase):
    def test_get_most_cancelled_date(self):
        event_1 = G(
            ticket_models.Event,
            name="Event 1",
            description="Hello!",
            event_date=date(2020, 10, 1),
        )
        event_2 = G(
            ticket_models.Event,
            name="Event 2",
            description="Hello!",
            event_date=date(2021, 10, 1),
        )
        event_3 = G(
            ticket_models.Event,
            name="Event 3",
            description="Hello!",
            event_date=date(1989, 10, 1),
        )

        ticket_type1 = G(
            ticket_models.TicketType, name="Early Bird", event=event_1, quantity=1
        )

        order_1 = G(
            ticket_models.Order,
            ticket_type=ticket_type1,
            quantity=1,
            state=ticket_constants.FULFILLED_STATE,
        )
        G(ticket_models.Ticket, ticket_type=ticket_type1, order=order_1)

        ticket_type2 = G(
            ticket_models.TicketType, name="Night Owl", event=event_2, quantity=2
        )
        order_2 = G(
            ticket_models.Order,
            ticket_type=ticket_type2,
            quantity=2,
            state=ticket_constants.CANCELLED_STATE,
        )
        G(ticket_models.Ticket, ticket_type=ticket_type2, order=order_2)
        G(ticket_models.Ticket, ticket_type=ticket_type2, order=order_2)

        ticket_type3 = G(
            ticket_models.TicketType, name="Night Owl", event=event_3, quantity=3
        )
        order_3 = G(
            ticket_models.Order,
            ticket_type=ticket_type3,
            quantity=3,
            state=ticket_constants.CANCELLED_STATE,
        )
        G(ticket_models.Ticket, ticket_type=ticket_type3, order=order_3)
        G(ticket_models.Ticket, ticket_type=ticket_type3, order=order_3)
        G(ticket_models.Ticket, ticket_type=ticket_type3, order=order_3)

        result = ticket_metrics.get_most_cancelled_date()
        expected_result = {
            "ticket_type__event__event_date": event_3.event_date,
            "cancelled_quantity": 3,
        }
        self.assertEqual(expected_result, result)

    def test_number_of_orders_and_cancellation_rate(self):
        event = G(
            ticket_models.Event,
            id=1,
            name="Event 1",
            description="Hello!",
            event_date=date(2020, 10, 1),
        )
        ticket_type1 = G(
            ticket_models.TicketType, name="Early Bird", event=event, quantity=12
        )

        G(
            ticket_models.Order,
            ticket_type=ticket_type1,
            quantity=3,
            state=ticket_constants.FULFILLED_STATE,
        )

        G(
            ticket_models.Order,
            ticket_type=ticket_type1,
            quantity=3,
            state=ticket_constants.FULFILLED_STATE,
        )

        G(
            ticket_models.Order,
            ticket_type=ticket_type1,
            quantity=3,
            state=ticket_constants.FULFILLED_STATE,
        )
        G(
            ticket_models.Order,
            ticket_type=ticket_type1,
            quantity=3,
            state=ticket_constants.CANCELLED_STATE,
        )

        result = ticket_metrics.number_of_orders_and_cancellation_rate(event.id)
        expected_result = {
            "total": 4,
            "cancellation_rate_percentage": Decimal("25"),
        }
        self.assertEqual(expected_result, result)
