from datetime import datetime
import pytz

from django.db import models, transaction
from django.db.models import Q
from django.conf import settings

from . import constants


class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    event_date = models.DateField(null=True)


class TicketType(models.Model):
    name = models.CharField(max_length=255)
    event = models.ForeignKey(
        Event, related_name="ticket_types", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1, editable=False)

    quantity.help_text = "The number of actual tickets available upon creation"

    def available_tickets(self):
        return self.tickets.filter(
            Q(order__isnull=True) | Q(order__state=constants.CANCELLED_STATE)
        )

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
        max_length=20,
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
        self.state_change_at = datetime.utcnow().replace(tzinfo=pytz.UTC)
        self.save(update_fields=["state", "state_change_at"])

    def cancel(self):
        time_difference = (
            datetime.utcnow().replace(tzinfo=pytz.UTC) - self.state_change_at
        )

        if time_difference.seconds >= 30 * 60:
            booked_tickets_qs = self.ticket_type.available_tickets().select_for_update(
                skip_locked=True
            )[: self.quantity]

            with transaction.atomic():
                self.state = constants.CANCELLED_STATE
                self.state_change_at = datetime.utcnow().replace(tzinfo=pytz.UTC)
                self.save(update_fields=["state", "state_change_at"])

    @property
    def is_cancelled(self) -> bool:
        if self.state == constants.CANCELLED_STATE:
            return True
        return False
