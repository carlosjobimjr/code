from django import template

register = template.Library()

@register.filter
def add_total_station_power(stations):
	power = float(0)
	for station in stations:
		power += float(station.get_station_power())

	return power

