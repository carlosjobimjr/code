from .utils import calculate_subprocess_totals, update_subprocess_message
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SubProcess
from .utils import update_subprocess_message
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SubProcess)
def subprocess_handler(sender, instance, created, **kwargs):
    try:
        channel_layer = get_channel_layer()
        room_group = f"SubProcess_{instance.process.id}"
        
        message = update_subprocess_message(instance)
        
        if message:  # Only send if we have valid data
            async_to_sync(channel_layer.group_send)(
                room_group, 
                {
                    'type': "update_message",
                    'message': message
                }
            )
        
    except Exception as e:
        logger.error(f"Error in subprocess_handler: {str(e)}")