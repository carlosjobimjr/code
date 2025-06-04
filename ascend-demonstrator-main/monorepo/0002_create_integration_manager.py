from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
	dependencies = []

	operations = [
		migrations.CreateModel(
			name='IntegrationManager',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
				verbose_name='ID')),
				('integration_name', models.CharField(max_length=100, unique=True)),
				('integration_watermark', models.BigIntegerField(blank=True, null=False, default=0)),
				('integration_last_run_at', models.DateTimeField(blank=True, null=True)),
			]
			),
	]