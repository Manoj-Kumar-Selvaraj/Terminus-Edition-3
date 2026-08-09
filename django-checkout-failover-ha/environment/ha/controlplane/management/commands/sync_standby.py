from django.core.management.base import BaseCommand

from controlplane.replica import apply_standby


class Command(BaseCommand):
    help = "Copy writer business rows onto the standby shop file."

    def handle(self, *args, **options) -> None:
        result = apply_standby()
        self.stdout.write(str(result))
