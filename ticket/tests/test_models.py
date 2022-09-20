from datetime import datetime, timedelta
import pytz
from sre_parse import State
from django.test import TestCase
from django_dynamic_fixture import G, F

from ticket.models import Event, TicketType, Order
from ticket import constants as ticket_constants


class TicketTypeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = G(Event)

    def test_avaialble_tickets(self):
        ticket_type = G(TicketType, name="Test", quantity=5, event=self.event)
        all_tickets = list(ticket_type.tickets.all())

        five_available_tickets = set(ticket_type.available_tickets())

        # book one ticket
        ticket = all_tickets[0]
        ticket.order = G(Order, ticket_type=ticket_type, quantity=1)
        ticket.save()

        four_available_tickets = set(ticket_type.available_tickets())

        self.assertCountEqual(five_available_tickets, all_tickets)
        self.assertCountEqual(four_available_tickets, set(all_tickets) - {ticket})

    def test_save(self):
        """Verifying that the save method creates Ticket(s) upon TicketType creation"""

        ticket_type_1 = G(TicketType, name="Without quantity", event=self.event)
        ticket_type_5 = G(TicketType, name="Test", quantity=5, event=self.event)

        one_ticket = ticket_type_1.tickets.count()
        five_tickets = ticket_type_5.tickets.count()

        self.assertEqual(one_ticket, 1)
        self.assertEqual(five_tickets, 5)


class OrderTest(TestCase):
    def test_book_tickets(self):
        order = G(Order, ticket_type=F(quantity=5), quantity=3)

        pre_booking_ticket_count = order.tickets.count()
        order.book_tickets()
        post_booking_ticket_count = order.tickets.count()

        with self.assertRaisesRegexp(Exception, r"Order already fulfilled"):
            order.book_tickets()

        self.assertEqual(pre_booking_ticket_count, 0)
        self.assertEqual(post_booking_ticket_count, 3)

    def test_order_cancellation_fails(self):
        order = G(Order, ticket_type=F(quantity=5), quantity=3)

        pre_booking_ticket_count = order.tickets.count()

        # book the tickets to fulfill the order
        order.book_tickets()
        # cancel the the order
        order.cancel()

        order.refresh_from_db()
        booking_ticket_count = order.tickets.count()

        self.assertEqual(booking_ticket_count, 3)
        self.assertEqual(order.state, ticket_constants.FULFILLED_STATE)

    def test_order_cancellation_successful(self):
        thirty_one_min_ago = datetime.utcnow() - timedelta(minutes=31)
        order = G(
            Order,
            ticket_type=F(quantity=5),
            quantity=2,
        )

        # book the tickets to fulfill the order
        order.book_tickets()

        # overwrite the state_change_at to make it cancellable
        order.state_change_at = thirty_one_min_ago.replace(tzinfo=pytz.UTC)
        order.save()

        order_quantity = order.tickets.count()

        # cancel the the order
        order.cancel()

        order.refresh_from_db()

        self.assertEqual(order.state, ticket_constants.CANCELLED_STATE)
        self.assertEqual(order.is_cancelled, True)
        self.assertEqual(order.quantity, order_quantity)
