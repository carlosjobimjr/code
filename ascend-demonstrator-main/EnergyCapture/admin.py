from django.contrib import admin
from .models import Equipment, EquipmentTime, Station, StationTime


admin.site.register(Station)
admin.site.register(Equipment)
admin.site.register(EquipmentTime)
admin.site.register(StationTime)