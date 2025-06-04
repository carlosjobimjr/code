from django import forms
from django.forms import TextInput, ModelForm
from Main.models import *
from MainData.models import *
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User, Group
from django.forms import ModelChoiceField
from decimal import Decimal
import logging

# Set up logger for this module
logger = logging.getLogger(__name__)

class ProjectConstants:
    """Constants and mappings for project management"""
    SUPER_CHOICES = {
        'NPW': ('nominalPartWeight', 'Nominal Part Weight'),
        # 'NPL': ('nominalPartLength', 'Nominal Length'),
        # 'NWI': ('nominalPartWidth', 'Nominal Width'),
        # 'NPT': ('nominalPartThickness', 'Nominal Thickness'),
        # 'TT': ('thicknessTolerance', 'Thickness Tolerance'),
        # 'WT': ('widthTolerance', 'Width Tolerance'),
        # 'LT': ('lengthTolerance', 'Length Tolerance'),
        # 'DT': ('depthTolerance', 'Depth Tolerance'),
        # 'TW': ('weightTolerance', 'Weight Tolerance'),
        # 'NVW': ('nominalVolumeWrinkling', 'Nominal Volume of Wrinkling'),
        # 'PWT': ('preformWrinklingTolerance', 'Preform Wrinkling Tolerance'),
        'MD': ('materialDensity', 'Material Density'),  
    }
    
    MANAGEMENT_CHOICES = {
        'THR': ('techRate', 'Technician Rate'),
        'SUR': ('superRate', 'Supervisor Rate'),
        'PWR': ('powerRate', 'Electricity Rate'),
        'SUC': ('setUpCost', 'Set Up Cost'),
        'BPN': ('baselinePartNo', 'Baseline Part Number'),
        'PKW': ('CO2PerPower', 'CO2 per KWH'),
        'WON': ('workOrderNumber', 'Work Order Number'),
        'PKG': ('priceKG', 'Price per KG'),         
        'PM2': ('priceM2', 'Price per M²'),         
    }

    @classmethod
    def get_choices_for_group(cls, group):
        """Get choices based on user group"""
        if group == "Management":
            return [(k, v[1]) for k, v in cls.MANAGEMENT_CHOICES.items()]
        elif group == "Supervisor":
            return [(k, v[1]) for k, v in cls.SUPER_CHOICES.items()]
        return []

    @classmethod
    def get_field_name(cls, group, choice):
        """Get database field name for a choice"""
        if group == "Management":
            choices_dict = cls.MANAGEMENT_CHOICES
        elif group == "Supervisor":
            choices_dict = cls.SUPER_CHOICES
        else:
            return None
            
        return choices_dict.get(choice, (None, None))[0]

class ConstForm(forms.Form):
    """Form for handling project constant changes"""
    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            print(f"Initializing ConstForm for group: {group}")  # Using print instead of logger
            
            choices = ProjectConstants.get_choices_for_group(group)
            if not choices:
                print(f"No choices found for group: {group}")
                return
                
            self.fields['choice'] = forms.ChoiceField(
                choices=choices,
                label='Choice',
                widget=forms.Select(),
                required=True
            )
            
            self.fields['value'] = forms.DecimalField(
                label='Value',
                widget=forms.TextInput(attrs={
                    'placeholder': 'Enter value',
                    'style': 'width:35vw;'
                }),
                decimal_places=3,
                required=True
            )
        except Exception as e:
            print(f"Error initializing ConstForm: {str(e)}")
            raise

    def clean(self):
        cleaned_data = super().clean()
        try:
            if 'value' in cleaned_data:
                value = Decimal(str(cleaned_data['value']))
                if value < 0:
                    raise forms.ValidationError("Value cannot be negative")
                cleaned_data['value'] = value.quantize(Decimal('0.001'))
        except (ValueError, TypeError):
            raise forms.ValidationError("Please enter a valid number")
        return cleaned_data

# [Rest of your existing form classes remain unchanged]
class CreateNewProject(forms.Form):
	"""A form to allow the user to create a new process"""

	name = forms.CharField(label='Name', max_length = 200, widget=forms.TextInput(attrs={'placeholder':'Enter Project Name', 'style':'width:30vw;'}))
	manual = forms.BooleanField(required=False)

class deleteProject(forms.Form):
	def __init__(self, company, *args, **kwargs):
		super(deleteProject, self).__init__(*args, **kwargs)
		self.fields['choice'] = forms.ModelChoiceField(queryset=company.project_set.all(), empty_label="Select Project Name", widget=forms.Select(attrs={'style':'height:2vw;'}))
	
class addManualInfo(forms.Form):
	"""A form to allow the user to add a manual input"""

	task = forms.ChoiceField(choices=SubProcess.MANUAL_INPUT_CHOICES, label='Task', widget=forms.Select(), required=True)
	value = forms.CharField(label='Value', max_length = 200, widget=forms.TextInput(attrs={'placeholder':'Enter Value', 'style':'width:13vw;'}))

	def clean(self): #error handling for incorrect data
		super(addManualInfo , self).clean()
		error_message = ''

		if self.cleaned_data['value'] == "0":
			error_message = 'Value should not be zero!'
			raise forms.ValidationError(error_message)

		try:
			error_message = "Value should be numeric!"
			float(self.cleaned_data['value']) #try convert input to float, if it fails then the user entered a non-numeric value
		except:
			raise forms.ValidationError(error_message)

		return self.cleaned_data

class addManualTimeInfo(forms.Form):
	"""A form to allow the user to add a manual input"""

	task = forms.ChoiceField(choices=SubProcess.MANUAL_INPUT_TIME_CHOICES, label='Task', widget=forms.Select(), required=True)

class EditComponent(forms.Form):
	"""Form to allow the editing of a component"""	
	
	name = forms.CharField(label='Name', max_length = 200, widget=forms.TextInput(attrs={'placeholder':'Enter Component', 'style':'width:30vw;'}))	

class ChangeGraphTime(forms.Form):
	time = forms.IntegerField(label='time', widget=forms.TextInput(attrs={'placeholder':'Enter Time in Seconds', 'style':'width:35vw;'}))

class EnterDeviceID(forms.Form): 
	name = forms.CharField(label='Device ID', max_length = 200, widget=forms.TextInput(attrs={'placeholder':'Enter Device ID', 'style':'width:30vw;'}))	
	
class addProcess(forms.Form):
	def __init__(self, project, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(addProcess, self).__init__(*args, **kwargs)
		self.fields['choice'] = forms.ModelChoiceField(queryset=PossibleProjectProcess.objects.all().filter(project=project))

class addManualProcess(ModelForm):
	"""A form to allow the user to add a prespecified process"""
	class Meta:
		model = Process
		fields = ['manualName']
		lables = {
			'manualName' : _('Name'),		
		}		
		widgets = {
				'manualName': forms.Select(attrs={
				'placeholder':'Process'
				})	
		}
		
class operatorForm(forms.Form):
	def __init__(self, name, *args, **kwargs):
		super(operatorForm, self).__init__(*args, **kwargs) #passing company name to form so model choice field can access all profiles within company
		company = Company.objects.get(company_name=name)
		newset = Profile.objects.all().filter(user_company=company)
		self.fields['choice'] = forms.ModelChoiceField(queryset=newset, empty_label="Choose a User")

class PartInstanceForm(forms.Form):
	def __init__(self, process, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(PartInstanceForm, self).__init__(*args, **kwargs)
		choices = []
		if process.partinstance_set.all():
			for inst in PartInstance.objects.all().filter(process=process):
				choices.append(('Part' + str(inst),'Part Instance: ' + str(inst.instance_id)))
		if process.blankinstance_set.all():
			for inst in BlankInstance.objects.all().filter(process=process):
				choices.append(('Blank' + str(inst),'Blank Instance: ' + str(inst.instance_id)))
		if process.plyinstance_set.all():
			for inst in PlyInstance.objects.all().filter(process=process):
				choices.append(('Ply' + str(inst),'Ply Instance: ' + str(inst.instance_id)))

		#print(choices)
		self.fields['choice'] = forms.ChoiceField(choices=choices, label='Choice', widget=forms.Select())

class PlyInstanceForm(forms.Form):
	def __init__(self, process, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(PlyInstanceForm, self).__init__(*args, **kwargs)
		self.fields['choice'] = forms.ModelChoiceField(queryset=Ply.objects.all().filter(submitted=False), empty_label="Choose a Ply")

class BlankInstanceFrom(forms.Form):
	def __init__(self, process, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(BlankInstanceForm, self).__init__(*args, **kwargs)
		self.fields['choice'] = forms.ModelChoiceField(queryset=Blank.objects.all().filter(submitted=False), empty_label="Choose a Blank")

class ProjectPartInstanceForm(forms.Form):
	def __init__(self, project, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(ProjectPartInstanceForm, self).__init__(*args, **kwargs)
		self.fields['choice'] = forms.ModelChoiceField(queryset=project.part_set.filter(submitted=False), empty_label="Choose a Part")

class addSubProcess(forms.Form):
	"""A form to allow the user to add a prespecified subprocess"""
	def __init__(self, process, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(addSubProcess, self).__init__(*args, **kwargs)
		self.fields['name'] = forms.ModelChoiceField(queryset=PossibleSubProcesses.objects.all().filter(process=process))

class addManualSubProcess(forms.Form):
	"""A form to allow the user to add a prespecified subprocess"""
	def __init__(self, process, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(addManualSubProcess, self).__init__(*args, **kwargs)
		self.fields['name'] = forms.ModelChoiceField(queryset=PossibleSubProcesses.objects.all().filter(process=process))

class SensorForm(forms.Form):
	def __init__(self, process, *args, **kwargs): #passing process into form so model choice field can access all part instances within process
		super(SensorForm, self).__init__(*args, **kwargs)
		self.fields['choice'] = forms.ModelChoiceField(queryset=PossibleSensors.objects.all().filter(process=process))

class PossibleSensorForm(ModelForm): 
	class Meta:
		model = PossibleSensors
		fields = ['name']

class ProcessSensorForm(ModelForm): 
	
	class Meta:
		model = Sensor
		fields = ['proName']
		labels = {
			'proName': ('Name'),		
		}
		
class MachineForm(ModelForm):
	
	class Meta:
		model = Machine
		fields = ['name']

class SelectSensorForm(forms.Form): #needs to be tested
	def __init__(self, sensorSet, *args, **kwargs): #passing sensor set for selection to be deleted (using model ID)
		super(SelectSensorForm, self).__init__(*args, **kwargs)

		self.fields['choice']=forms.ModelChoiceField(queryset=sensorSet.values_list('modelID', flat=True), empty_label="Select A Sensor to delete!", required=True)

class WeightAssessmentForm(forms.Form):
    actual_weight = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter actual weight (kg)',
            'step': '0.001'
        })
    )
    tolerance = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tolerance (%)',
            'step': '0.01'
        })
    )
    
class PreviousMaterialForm(forms.Form):

#	choice = forms.ChoiceField(choices=Project.PREV_MATERIAL_CHOICES, label='Choice', widget=forms.Select(), required=True)
	value = forms.DecimalField(label='Value', widget=forms.TextInput(attrs={'placeholder':'Enter value', 'style':'width:35vw;'}))


class EnterPartWeight(forms.Form):#needs to be tested
	
	value = forms.IntegerField(label='Weight', widget=forms.TextInput(attrs={'placeholder':'Enter weight', 'style':'width:35vw;'}))

class AddMaterialForm(ModelForm):#needs to be tested
	
	class Meta:
		model = Material
		fields = ['name']
		widgets = {
				'name': forms.Select(attrs={
				'placeholder':'Material'
				})	
		}


class SubMasterForm(forms.Form):
	def __init__(self, name, *args, **kwargs): #passing subprocess name to access specific fields for each sub process
		super(SubMasterForm, self).__init__(*args, **kwargs)
		if name == "Material and Tool Inside Press":
			self.fields['choice'] = forms.ChoiceField(choices=SubProcess.MATERIAL_IN_PRESS_CHOICES, label = 'Choice', widget=forms.Select(), required=True)
			self.fields['value'] = forms.DecimalField(label='value', widget=forms.TextInput(attrs={'placeholder':'Enter value', 'style':'width:5.5vw;'}))
		elif name == "Material Pressed":
			self.fields['choice'] = forms.ChoiceField(choices=SubProcess.MATERIAL_PRESSED_CHOICES, label = 'Choice', widget=forms.Select(), required=True)
			self.fields['value'] = forms.DecimalField(label='value', widget=forms.TextInput(attrs={'placeholder':'Enter value', 'style':'width:5.5vw;'}))
		elif name == "Removal End effector actuated":
			self.fields['choice'] = forms.ChoiceField(choices=SubProcess.REMOVAL_EFFECTOR_CHOICES, label = 'Choice', widget=forms.Select(), required=True)
			self.fields['value'] = forms.DecimalField(label='value', widget=forms.TextInput(attrs={'placeholder':'Enter value', 'style':'width:5.5vw;'}))
		elif name == "Final Inspection":
			self.fields['choice'] = forms.ChoiceField(choices=SubProcess.TRIMMING_CHOICES, label = 'Choice', widget=forms.Select(), required=True)
			self.fields['value'] = forms.DecimalField(label='value', widget=forms.TextInput(attrs={'placeholder':'Enter value', 'style':'width:5.5vw;'}))
			
class ProcessWindowForm(forms.Form):
	
	value = forms.BooleanField(required = False)
