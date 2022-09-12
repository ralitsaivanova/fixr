from datetime import datetime

from django.db import models, transaction
from django.conf import settings

import constants


class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()


class TicketType(models.Model):
    name = models.CharField(max_length=255)
    event = models.ForeignKey(
        Event, related_name="ticket_types", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1, editable=False)

    quantity.help_text = "The number of actual tickets available upon creation"

    def available_tickets(self):
        return self.tickets.filter(order__isnull=True)

    def save(self, *args, **kwargs):
        new = not self.pk
        super().save(*args, **kwargs)
        if new:
            self.tickets.bulk_create([Ticket(ticket_type=self)] * self.quantity)


class Ticket(models.Model):
    ticket_type = models.ForeignKey(
        TicketType, related_name="tickets", on_delete=models.CASCADE
    )
    order = models.ForeignKey(
        "ticket.Order",
        related_name="tickets",
        default=None,
        null=True,
        on_delete=models.SET_NULL,
    )


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.PROTECT
    )
    ticket_type = models.ForeignKey(
        TicketType, related_name="orders", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()
    state = models.CharField(
        choices=constants.ORDER_STATES,
        default=constants.CREATED_STATE,
    )
    state_change_at = models.DateTimeField(null=True)

    def book_tickets(self):
        if self.state == constants.FULFILLED_STATE:
            raise Exception("Order already fulfilled")
        qs = self.ticket_type.available_tickets().select_for_update(skip_locked=True)[
            : self.quantity
        ]
        try:
            with transaction.atomic():
                updated_count = self.ticket_type.tickets.filter(id__in=qs).update(
                    order=self
                )
                if updated_count != self.quantity:
                    raise Exception
        except Exception:
            return

        self.state = constants.FULFILLED_STATE
        self.state_change_at = datetime.utcnow()
        self.save(update_fields=["state", "state_change_at"])
