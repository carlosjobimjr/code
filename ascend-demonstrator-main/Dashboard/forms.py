from django import forms
from django.forms import TextInput, ModelForm
from . models import * 
from MainData.models import *
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from Main.models import *
from .widget import DatePickerInput, TimePickerInput, DateTimePickerInput

# Define the metric choices tuple
METRIC_CHOICES = (
    ('CYT', 'Cycle Time'),
    ('PRT', 'Process Time'),
    ('INT', 'Interface Time'),
    ('SCR', 'Scrap Rate'),
    ('TLR', 'Technician Labour'),
    ('SLR', 'Supervisor Labour'),
    ('PWR', 'Power Consumption')
)

# Define the metric dictionary
metric_dict = {
    'CYT': 'cycleTime',
    'PRT': 'processTime',
    'INT': 'interfaceTime',
    'SCR': 'scrapRate',
    'TLR': 'techLabour',
    'SLR': 'superLabour',
    'PWR': 'powerConsumption'
}

class MetricForm(forms.Form):
    """A form to allow the user to change the metric being displayed on the sub process chart"""
    choice = forms.ChoiceField(choices=METRIC_CHOICES, label='Choice', widget=forms.Select(), required=True)

class AssumedCostForm(forms.Form):
    value = forms.IntegerField(
        label='Value',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Value in K Pounds',
            'style': 'width:10vw;'
        })
    )

class LearningRateForm(forms.Form):
    value = forms.FloatField(
        label='Value',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Learning Rate (%)',
            'style': 'width:10vw;'
        })
    )


class ManualProjectComparisonForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super(ManualProjectComparisonForm, self).__init__(*args, **kwargs)
        projectSet = Project.objects.none()
        projectSet = user.profile.user_company.project_set.all().filter(manual=True)
        
        # Modify the queryset to emphasize 'Manual Project'
        self.fields['choice'] = forms.ModelChoiceField(
            queryset=projectSet, 
            empty_label="Select a Project",
            to_field_name='id',  # Ensure we're selecting by project ID
            widget=forms.Select(attrs={
                'class': 'block w-full p-2 text-sm text-gray-900 border border-gray-300 rounded-lg bg-gray-50 focus:ring-blue-500 focus:border-blue-500'
            })
        )
	



class TimesForm(forms.Form):
	start_date_field = forms.DateField(widget=DatePickerInput)
	end_date_field = forms.DateField(widget=DatePickerInput)


class OEEParametersForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Select start date'
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text='Select start time'
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Select end date'
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text='Select end time'
    )
    planned_down_time = forms.FloatField(
        required=False,
        initial=-20,
        help_text='Default is -20 seconds'
    )
    theoretical_cycle_time = forms.FloatField(
        required=False,
        initial=180,
        help_text='Default is 180 seconds (3 minutes)'
    )
    number_of_shifts = forms.IntegerField(label='Number of Shifts', min_value=1)
    hours_per_shift = forms.FloatField(label='Hours per Shift', min_value=1)
