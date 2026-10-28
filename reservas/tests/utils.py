from datetime import datetime, time, timedelta

from django.utils import timezone


def manana_a_las(hora, dias=1):
    """Datetime local (aware) de dentro de `dias` días a la hora indicada."""
    dia = timezone.localdate() + timedelta(days=dias)
    return timezone.make_aware(datetime.combine(dia, time(hora)))
