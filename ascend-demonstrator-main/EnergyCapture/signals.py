from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.contrib.sessions.models import Session
from asgiref.sync import async_to_sync, sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django_celery_beat.models import PeriodicTask
from .models import StationTime, EquipmentTime, PowerClampTime


@receiver(signal=post_delete, sender=Session)
def disable_all_periodic_task_under_the_session(sender, instance, **kwargs):
	print("Session Key ", instance.session_key)
	periodic_qs = PeriodicTask.objects.filter(
		name__istartswith=f"send-co2-and-khw-data-to-socket-{instance.session_key}"
	)
	periodic_qs.update(enabled=True)

	# will be disabling all other periodic tasks later onwards


@receiver(signal=post_save, sender=PowerClampTime)
def create_an_equipment_time_instance(sender, instance, created, **kwargs):
	if created:
		equipment = instance.powerClamp.equipment
		equipment_time_obj = equipment.equipmenttime_set.create(power=instance.power)
		return equipment_time_obj
	return None



@receiver(signal=post_save, sender=EquipmentTime)
def create_station_time_instance(sender, instance, created, **kwargs):
	if created:
		station = instance.equipment.station
		station_time_obj = station.stationtime_set.create(power=instance.power)
		return station_time_obj

	return None
