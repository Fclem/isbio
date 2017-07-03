from decimal import Decimal
from django import forms
from django.db.models import Q
from django.conf import settings
from django.contrib.admin import widgets
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ValidationError
import breeze.models
import datetime
import json
import re
import rora
import xml.etree.ElementTree as Xml
# from bootstrap_toolkit.widgets import BootstrapTextInput, BootstrapPasswordInput
# from django.core import mail
# from validate_email import validate_email
# from django.forms import FileField
# from django.forms import extras
# from django.template.defaultfilters import default
# import logging
# from sys import stdout
# import copy


class NewProjectForm(forms.Form):
	project_name = forms.CharField(
		max_length=50,
		widget=forms.TextInput(attrs={'placeholder': ' Project Name ', })
	)

	project_manager = forms.CharField(
		max_length=50,
		widget=forms.TextInput(attrs={'placeholder': ' Project Manager ', })
	)

	principal_investigator = forms.CharField(
		label=u'PI',
		max_length=50,
		widget=forms.TextInput(attrs={'placeholder': ' Principal Investigator ', })
	)

	collaborative = forms.BooleanField(
		required=False,
		help_text="Visible by the other users"
	)

	eid = forms.CharField(
		label=u'External ID',
		max_length=50,
		required=False,
		widget=forms.TextInput(attrs={'placeholder': ' optional ', })
	)

	wbs = forms.CharField(
		label=u'WBS',
		max_length=50,
		required=False,
		widget=forms.TextInput(attrs={'placeholder': ' optional ', })
	)

	description = forms.CharField(
		widget=forms.Textarea(attrs={'cols': 15, 'rows': 2, 'placeholder': 'optional'}),
		required=False
	)

	def clean_project_name(self):
		project_name = self.cleaned_data.get('project_name')
		try:
			breeze.models.Project.objects.get(name=project_name)
		except breeze.models.Project.DoesNotExist:
			return project_name
		else:
			raise forms.ValidationError("That project name already exists.")


class EditProjectForm(forms.Form):
	eid = forms.CharField(
		label=u'External ID',
		max_length=50,
		required=False,
		widget=forms.TextInput(attrs={'placeholder': ' optional ', })
	)

	wbs = forms.CharField(
		label=u'WBS',
		max_length=50,
		required=False,
		widget=forms.TextInput(attrs={'placeholder': ' optional ', })
	)

	description = forms.CharField(
		widget=forms.Textarea(attrs={'cols': 15, 'rows': 2, 'placeholder': 'optional'}),
		required=False
	)


# FIXME broken
class AbstractFormValidator(forms.Form):
	"""
	def __init__(self, *args, **kwargs):
		super(AbstractFormValidator, self).__init__(*args, **kwargs)
		self.model = self.Meta.model

	def clean(self):
		cleaned_data = super(AbstractFormValidator, self).clean()
		if hasattr(self.model, 'RESERVED') and self.model.RESERVED.keys():
			# for field_name, values in set(self.model.RESERVED.keys()) & set(cleaned_data.keys()):
			keys = list(set(self.model.RESERVED.keys()) & set(cleaned_data.keys()))
			for field_name in keys:
				value, data = self.model.RESERVED[field_name], cleaned_data[field_name]
				if data.lower() in value:
					self.add_error(None, "%s is a reserved value for field %s" % (data, field_name))
					raise forms.ValidationError("%s is a reserved value for field %s" % (data, field_name))
		return cleaned_data
	"""
	pass


# clem 18/04/2016
class ReportPropsFormMixin(object):
	FIELD_SHARED = 'shared'
	FIELD_SHARED_GROUPS = 'shared_g'
	FIELD_TARGET = 'target'
	FIELD_PROJECT = 'project'
	request = None
	_share_options = None
	_share_options_ppl = None
	_share_options_group = None
	_target_list = None
	_project_qs = None
	
	# clem 19/04/2016
	def __init__(self, *args, **kwargs):
		self.request = self.request or kwargs.pop('request', None)
		if self.request:
			self.author = self.request.user
		super(ReportPropsFormMixin, self).__init__(*args, **kwargs)
	
	# clem 19/01/2017
	def users_list_of_tuples_gen(self, prefix='', user_list=None):
		a_list = list()
		
		user_list = user_list or self._user_only_list_query
		
		for ur in user_list:
			a_list.append(tuple(('%s%s' % (prefix, ur.id), ur.get_full_name() or ur.username)))
		
		return a_list
	
	# clem 19/01/2017
	@property
	def _users_list_of_tuples(self):
		return self.users_list_of_tuples_gen('u')
	
	# clem 19/01/2017
	def group_list_of_tuples_gen(self, prefix='', group_list=None):
		a_list = list()
		
		group_list = group_list or self._group_list_query
		
		for gr in group_list:
			a_list.append(tuple(('%s%s' % (prefix, gr.id), gr.name)))
		
		return a_list
	
	# clem 19/01/2017
	@property
	def _group_list_of_tuples(self):
		return self.group_list_of_tuples_gen('g')
	
	@property
	def share_options(self):
		if not self._share_options:
			self._share_options = list()
			spe_groups = self.group_list_of_tuples_gen('g', group_list=breeze.models.Group.objects.get_specials())
			self._share_options.append(tuple(('Special groups', tuple(spe_groups))))
			groups = self._group_list_of_tuples
			if groups:
				self._share_options.append(tuple(('Groups', tuple(groups))))
			users = self._users_list_of_tuples
			if users:
				self._share_options.append(tuple(('Individual Users', tuple(users))))
		return self._share_options
	
	# clem 19/04/2016
	@property
	def target_list(self): # code moved to ReportType.target_list
		return breeze.models.ReportType.objects.get(type=self.request.rtype).all_as_form_list
	
	def _sup_init_(self, *_, **kwargs):
		# FIXME obsolete
		if not self.request and 'request' in kwargs:
			self.request = kwargs.get("request")
		if not hasattr(self, 'fields'):
			self.fields = dict()
		
		rq = breeze.models.Project.objects.available(self.request.user)
		
		# FIXME : use manager instead
		self.fields[self.FIELD_PROJECT] = forms.ModelChoiceField(
			queryset=rq,
			initial=rq[0] if len(rq) == 1 else None,
			widget=forms.Select()
		)
		
		self.fields[self.FIELD_TARGET] = forms.ChoiceField(
			choices=self.target_list,
			initial=self.target_list[0],
			widget=forms.Select()
		)
		
		# self.fields["Share"] = forms.MultipleChoiceField( # TODO find out why this has various spelling
		self.fields[self.FIELD_SHARED] = forms.MultipleChoiceField(
			required=False,
			choices=self.share_options,
			widget=forms.SelectMultiple(
				attrs={'class': 'multiselect', }
			)
		)
	
	# clem 12/05/2017
	@property
	def _user_only_list_query(self):
		""" Override to user list that is usually stripped of current user, except when user is superuser

		:return:
		:rtype:
		"""
		if self.request.user.is_superuser:
			return breeze.models.OrderedUser.objects.all_but_guests()
		else:
			return breeze.models.OrderedUser.objects.all_but_user(self.request.user, include_guests=False)
	
	# clem 12/05/2017
	@property
	def _user_guest_list_query(self):
		return breeze.models.OrderedUser.objects.guests()
	
	# clem 12/05/2017
	@property
	def _group_list_query(self):
		if self.request.user.is_superuser:
			query = breeze.models.Group.objects.all_but_special()
		else:
			query = breeze.models.Group.objects.get_owned(self.request.user)
		return query.order_by("name")
	
	# clem 12/05/2017
	@property
	def _group_special_list_query(self):
		return breeze.models.Group.objects.get_specials().order_by("name")
	
	# clem 12/05/2017
	@property
	def _group_list_owned_query(self):
		return breeze.models.Group.objects.get_owned(self.request.user).order_by("name")
	
	# clem 12/05/2017
	@property
	def _group_list_others_query(self):
		return breeze.models.Group.objects.get_others(self.request.user).order_by("name")
	
	# clem 12/05/2017
	@property
	def user_share_options_grouped_guests(self):
		a_list = list()
		user_list = self.users_list_of_tuples_gen(user_list=self._user_only_list_query)
		guest_query = self._user_guest_list_query
		if guest_query.count():
			guest_list = self.users_list_of_tuples_gen(user_list=guest_query)
			a_list.append(tuple(('Users', user_list)))
			a_list.append(tuple(('Guests', guest_list)))
		else:
			a_list = user_list
		return a_list
	
	# clem 12/05/2017
	@property
	def group_share_options_grouped_ownership(self):
		a_list = list()
		special_query = self._group_special_list_query
		special_groups = self.group_list_of_tuples_gen(group_list=special_query)
		own_query = self._group_list_owned_query
		own_groups = self.group_list_of_tuples_gen(group_list=own_query)
		others_query = self._group_list_others_query
		others_groups = self.group_list_of_tuples_gen(group_list=others_query)
		a_list.append(tuple(('Special groups', special_groups)))
		if own_query.count():
			a_list.append(tuple(('My groups', own_groups)))
		if others_query.count():
			a_list.append(tuple(('Others\'', others_groups)))
		return a_list


class GroupForm(ReportPropsFormMixin, forms.Form):
	name = forms.CharField(
		max_length=50,
		widget=forms.TextInput(attrs={'placeholder': ' Group Name ', })
	)

	group_team = forms.ModelMultipleChoiceField(
		required=False,
		queryset=breeze.models.OrderedUser.objects.all(),
		widget=forms.SelectMultiple(
			attrs={'class': 'multiselect', }
		)
	)

	def __init__(self, *args, **kwargs):
		super(GroupForm, self).__init__(*args, **kwargs)
		self.fields['group_team'].choices = self.users_list_of_tuples_gen()
	
	def clean_name(self):
		group_name = self.cleaned_data.get('name')
		try:
			breeze.models.Group.objects.get(name=group_name, author=self.author)
		except breeze.models.Group.DoesNotExist:
			return group_name
		self.add_error('name', "You already have a group with this name !") # TODO test
		raise forms.ValidationError("You already have a group with this name !")
	
	# FIXME
	"""
	def clean(self):
		cleaned_data = super(GroupForm, self).clean()
		group_name = cleaned_data.get('name')
		try:
			breeze.models.Group.objects.get(name=group_name, author=self.author)
		except breeze.models.Group.DoesNotExist:
			return cleaned_data
		self.add_error('name', "You already have a group with this name !")
		# raise forms.ValidationError("You already have a group with this name !")
	"""
	
	class Meta(object):
		model = breeze.models.Group


class EditReportAccessForm(forms.Form): # FIXME obsolete & not in use anymore
	access_list = forms.ModelMultipleChoiceField(
		# required=True, # implicit
		queryset=breeze.models.OrderedUser.objects.all(),
		widget=forms.SelectMultiple(
			attrs={'class': 'multiselect', }
		)
	)


class SendReportTo(forms.Form):
	def __init__(self, *args, **kwargs):
		self.request = kwargs.pop("request")
		super(SendReportTo, self).__init__(*args, **kwargs)

		users_list_of_tuples = list()

		for ur in breeze.models.OffsiteUser.objects.filter(belongs_to=self.request.user):
			users_list_of_tuples.append(tuple((ur.id, ur.full_name + ' ( ' + ur.email + ' )')))

		send_options = list()
		send_options.append(tuple(('Registered Off-Site users', tuple(users_list_of_tuples))))

		self.fields["recipients"] = forms.MultipleChoiceField(
			choices=send_options,  # queryset=breeze.models.CustomUser.objects.all(),
			widget=forms.SelectMultiple(
				attrs={'class': 'multiselect', }
			)
		)

	class Meta(object):
		model = breeze.models.OffsiteUser
"""
class AddOffsiteUserDialog(forms.ModelForm):
	class Meta(object):
		model = breeze.models.OffsiteUser
		fields = ('email', )

		def clean_email(self):
			email = self.cleaned_data['email']
			return email

		def clean(self):
			self.email = self.clean_email()
			return self.cleaned_data

	widgets = {
		'email': forms.EmailField(label=u'Email Address', required=True),
	}
"""


class AddOffsiteUserDialog(forms.Form):
	def __init__(self, *args, **kwargs):
		super(AddOffsiteUserDialog, self).__init__(*args, **kwargs)

	email = forms.EmailField(label=u'Email Address', required=True)
	"""
	def clean_email(self):
		data = self.cleaned_data['email']
		logger = logging.getLogger('validate_email')
		ch = logging.StreamHandler(stream=stdout)
		ch.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		ch.setFormatter(formatter)
		logger.addHandler(ch)
		if not validate_email(data, debug=settings.DEBUG, check_mx=True):
			ch.flush()
			raise forms.Validation_Error("This mail address is non-existent!")

		return data
	"""


class AddOffsiteUser(forms.ModelForm):
	def __init__(self, user, *args, **kwargs):
		super(AddOffsiteUser, self).__init__(*args, **kwargs)
		# self.fields['shiny_access'].queryset = self.fields['shiny_access'].queryset = \
		# breeze.models.Report.objects.filter(type__type='ScreenReport', author_id=user.id)

	class Meta(object):
		model = breeze.models.OffsiteUser
		exclude = ['belongs_to', 'user_key', 'added_by', 'shiny_access']

	def clean(self):
		return self.cleaned_data

	widgets = {
		'email': forms.EmailField(label=u'Email Address', required=True),
		# 'shiny_access': forms.SelectMultiple(attrs={'class': 'multiselect' }),
	}
	# queryset = breeze.models.User.objects.all(),


class EditReportSharing(ReportPropsFormMixin, forms.ModelForm):
	author_id = 0
	
	def __init__(self, *args, **kwargs):
		super(EditReportSharing, self).__init__(*args, **kwargs)
		instance = kwargs.get('instance', None)
		self.author_id = instance.author.id if instance else self.request.user if self.request else 0
		self.fields[self.FIELD_SHARED].label = 'Individuals: '
		self.fields[self.FIELD_SHARED].choices = self.user_share_options_grouped_guests
		self.fields[self.FIELD_SHARED_GROUPS].label = 'Groups: '
		self.fields[self.FIELD_SHARED_GROUPS].choices = self.group_share_options_grouped_ownership
		
		self.widgets = {
			self.FIELD_SHARED:   forms.SelectMultiple(
				attrs={'class': 'multiselect', }, ),
			self.FIELD_SHARED_GROUPS: forms.SelectMultiple(
				attrs={'class': 'multiselect', }, )
		}
	
	class Meta(object):
		model = breeze.models.Report
		fields = ('shared', 'shared_g')
	
	
class EditGroupForm(ReportPropsFormMixin, forms.Form):
	def __init__(self, *args, **kwargs):
		super(EditGroupForm, self).__init__(*args, **kwargs)
		self.fields['group_team'].choices = self.users_list_of_tuples_gen()
	
	group_team = forms.ModelMultipleChoiceField(
		required=False,
		queryset=breeze.models.OrderedUser.objects.all(),
		widget=forms.SelectMultiple(
			attrs={ 'class': 'multiselect', }
		)
	)


# TODO convert into class generator
# clem 18/04/2016
class ReportPropsFormMixinWrapperOne(ReportPropsFormMixin, forms.Form):
	def __init__(self, *args, **kwargs):
		super(ReportPropsFormMixinWrapperOne, self).__init__(*args, **kwargs)
		self._sup_init_(*args, **kwargs)
	

# TODO convert into class generator
# clem 18/04/2016
class ReportPropsFormMixinWrapperTwo(ReportPropsFormMixin, forms.ModelForm):
	def __init__(self, *args, **kwargs):
		super(ReportPropsFormMixinWrapperTwo, self).__init__(*args, **kwargs)
		self._sup_init_(*args, **kwargs)


class ReportPropsForm(ReportPropsFormMixinWrapperOne):
	def __init__(self, *args, **kwargs):
		super(ReportPropsForm, self).__init__(*args, **kwargs)


class ReportPropsFormRE(ReportPropsFormMixinWrapperTwo):
	def __init__(self, *args, **kwargs):
		if 'instance' in kwargs: # initialize selection on the merged sharign field
			kwargs['initial'] = {self.FIELD_SHARED: kwargs['instance'].shared_data_in_form_format}
		super(ReportPropsFormRE, self).__init__(*args, **kwargs)

	class Meta(object):
		model = breeze.models.Report
		fields = ()


class RegistrationForm(forms.ModelForm):
	def __init__(self, *args, **kw):
		super(RegistrationForm, self).__init__(*args, **kw)
		self.fields.keyOrder = [
			'username',
			'email',
			'first_name',
			'last_name',
			'fimm_group',
			'password',
			'password1']

	username = forms.CharField(label=u'User Name')
	email = forms.EmailField(label=u'Email Address')
	password = forms.CharField(label=u'Password', widget=forms.PasswordInput())
	password1 = forms.CharField(label=u'Verify Password', widget=forms.PasswordInput())

	class Meta(object):
		model = breeze.models.UserProfile
		exclude = ('user', 'logo')

	def clean_username(self):
		username = self.cleaned_data['username']
		try:
			User.objects.get(username=username)
		except User.DoesNotExist:
			return username
		else:
			raise forms.ValidationError("That user name is already taken.")

	def clean(self):
		password = self.cleaned_data.get('password', None)
		password1 = self.cleaned_data.get('password1', None)
		if password and password1 and (password == password1):
			return self.cleaned_data
		else:
			raise forms.ValidationError("The passowords did not match. Please try again.")


class PersonalInfo(forms.Form):
	def __init__(self, *args, **kwargs):
		super(PersonalInfo, self).__init__(*args, **kwargs)
		# print(kwargs)

		self.fields['first_name'] = forms.CharField(
			max_length=55,
			widget=forms.TextInput(attrs={'placeholder': ' First Name ', })
		)
		self.fields['last_name'] = forms.CharField(
			max_length=55,
			widget=forms.TextInput(attrs={'placeholder': ' Last Name ', })
		)
		self.fields['email'] = forms.EmailField(
			max_length=75,
			widget=forms.TextInput(attrs={'placeholder': ' first.last@helsinki.fi ', })
		)
		institute_list = list()
		# institute_list.append(tuple((0, "Unknwown")))
		for each in breeze.models.Institute.objects.exclude(id=breeze.models.Institute.get_guest_institute().id):
			institute_list.append(tuple((each.id, each.institute)))
		if not len(institute_list):
			institute_list.append(tuple((0, "Unknwown")))

		self.fields['institute'] = forms.ChoiceField(
			required=False,
			initial=institute_list[0],
			choices=institute_list,
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

	def clean_institute(self):
		institute_id = self.cleaned_data['institute']
		try:
			_ = breeze.models.Institute.objects.get(pk=institute_id)
			return institute_id
		except (breeze.models.Institute.DoesNotExist, ObjectDoesNotExist):
			raise ValidationError("This is not a valid selection.")


class PatientInfo(forms.Form):
	def __init__(self, *args, **kwargs):

		super(PatientInfo, self).__init__(*args, **kwargs)

		self.fields['patient_id'] = forms.IntegerField(
			required=False,
			label="Patient ID",
			widget=forms.TextInput(attrs={'placeholder': ' ID ', 'readonly': True, })
		)

		self.fields['identifier'] = forms.CharField(
			max_length=75,
			label="Indentifier",
			widget=forms.TextInput(attrs={'placeholder': ' Indentifier ', })
		)

		self.fields['source'] = forms.CharField(
			max_length=75,
			label="Source",
			widget=forms.TextInput(attrs={'placeholder': ' Source ', })
		)

		self.fields['description'] = forms.CharField(
			required=False,
			max_length=7500,
			label="Description",
			widget=forms.Textarea(attrs={'cols': 15, 'rows': 2, 'placeholder': 'Description'})
		)

		organism_list = list()
		organisms = json.loads(rora.organism_data()[0])
		for ID, name in zip(organisms[0]['ORGANISM_ID'], organisms[1]['DESCRIPTION']):
			organism_list.append(tuple((ID, name)))
		# print(organisms)
		self.fields['organism'] = forms.ChoiceField(
			required=False,
			choices=organism_list,
			# initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		sex_list = list()
		sex = json.loads(rora.sex_data()[0])

		sex_list.append(tuple((0, 'Unkown')))
		for ID, name in zip(sex[0]['SEX_ID'], sex[1]['DESCRIPTION']):
			sex_list.append(tuple((ID, name)))

		self.fields['sex'] = forms.ChoiceField(
			required=False,
			choices=sex_list,
			# initial=0,
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)
		# print(organism_list[0][0])

		self.fields['birthdate'] = forms.DateField(
			widget=widgets.AdminDateWidget(),
			initial=datetime.date.today()
		)


class ScreenGroupInfo(forms.Form):
	def __init__(self, *args, **kwargs):
		super(ScreenGroupInfo, self).__init__(*args, **kwargs)
		# screen group info
		screen_list = list()
		screen = json.loads(rora.get_all_screens()[0])
		for ID, name in zip(screen[0]['PK_SCREEN_ID'], screen[1]['BREEZE_ALIAS']):
			screen_list.append(tuple((ID, name)))

		self.fields['dst'] = forms.MultipleChoiceField(
			required=False,
			choices=screen_list,
			label='Group Content',
			widget=forms.SelectMultiple(
				attrs={'class': 'multiselect', }
			)
		)


class ScreenInfo(forms.Form):
	def __init__(self, *args, **kwargs):

		super(ScreenInfo, self).__init__(*args, **kwargs)

		self.fields['screen_id'] = forms.IntegerField(  # required=False,
			label="Sreen ID",
			widget=forms.TextInput(attrs={'placeholder': ' ID ', 'readonly': True, })
		)

		self.fields['identifier'] = forms.CharField(
			max_length=75,
			label="Indentifier",
			widget=forms.TextInput(attrs={'placeholder': ' Indentifier ', 'readonly': True})
		)

		self.fields['description'] = forms.CharField(
			required=False,
			max_length=7500,
			label="Description",
			widget=forms.Textarea(attrs={'cols': 15, 'rows': 2, 'placeholder': 'Description', 'readonly': True})
		)

		self.fields['source_id'] = forms.CharField(
			required=False,
			max_length=75,
			label="Source ID",
			widget=forms.TextInput(attrs={'placeholder': ' Source ID', 'readonly': True})
		)

		self.fields['source'] = forms.CharField(
			max_length=75,
			label="Source",
			widget=forms.TextInput(attrs={'placeholder': ' Source ', 'readonly': True})
		)

		self.fields['protocol'] = forms.CharField(
			required=False,
			max_length=75,
			label="Protocol",
			widget=forms.TextInput(attrs={'placeholder': ' Protocol ', 'readonly': True})
		)

		patient_list = list()
		patients = json.loads(rora.get_all_patient()[0])
		for ID, name in zip(patients[0]['PK_ENTITY_ID'], patients[1]['IDENTIFIER']):
			patient_list.append(tuple((ID, name)))

		self.fields['patient'] = forms.ChoiceField(
			required=False,
			choices=patient_list,
			label='Patient',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		self.fields['alias'] = forms.CharField(  # required=False,
			max_length=75,
			label="Breeze Alias",
			widget=forms.TextInput(attrs={'placeholder': ' Breeze Alias '})
		)

		# sample type
		st_list = list()
		st = json.loads(rora.sample_type()[0])
		for ID, name in zip(st[0]['SAMPLE_TYPE_ID'], st[1]['DESCRIPTION']):
			st_list.append(tuple((ID, name)))

		self.fields['st'] = forms.ChoiceField(
			required=False,
			choices=st_list,
			label='Sample Type',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		# disease sub type
		dst_list = list()
		dst = json.loads(rora.disease_sub_type()[0])
		for ID, name in zip(dst[0]['DISEASE_SUB_TYPE_ID'], dst[1]['DESCRIPTION']):
			dst_list.append(tuple((ID, name)))
		self.fields['dst'] = forms.ChoiceField(
			required=False,
			choices=dst_list,
			label='Disease Sub Type',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)
		# media type
		mt_list = list()

		mt = json.loads(rora.media_type()[0])
		for ID, name in zip(mt[0]['MEDIA_TYPE_ID'], mt[1]['DESCRIPTION']):
			mt_list.append(tuple((ID, name)))
		self.fields['mt'] = forms.ChoiceField(
			required=False,
			choices=mt_list,
			label='Media Type',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)
		# histology
		history_list = list()

		history = json.loads(rora.histology()[0])
		for ID, name in zip(history[0]['HISTOLOGY_ID'], history[1]['DESCRIPTION']):
			history_list.append(tuple((ID, name)))

		self.fields['histology'] = forms.ChoiceField(
			required=False,
			choices=history_list,
			label='Histology',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		# disease state
		d_state_list = list()
		d_state = json.loads(rora.disease_state_data()[0])
		for ID, name in zip(d_state[0]['DISEASE_STATE_ID'], d_state[1]['DESCRIPTION']):
			d_state_list.append(tuple((ID, name)))

		self.fields['dstate'] = forms.ChoiceField(
			required=False,
			choices=d_state_list,
			label='Disease State',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		# experiment type
		et_list = list()
		et = json.loads(rora.experiment_type_data()[0])

		for ID, name in zip(et[0]['EXPERIMENT_TYPE_ID'], et[1]['DESCRIPTION']):
			et_list.append(tuple((ID, name)))

		self.fields['et'] = forms.ChoiceField(
			required=False,
			choices=et_list,
			label='Experiment Type',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		# plate count

		self.fields['plate_count'] = forms.IntegerField(  # required=False,
			label="Plate Count",
			widget=forms.TextInput(attrs={'placeholder': ' Plate Count '})
		)

		# disease grade

		dg_list = list()
		dg = json.loads(rora.disease_grade_data()[0])

		for ID, name in zip(dg[0]['DISEASE_GRADE_ID'], dg[1]['DESCRIPTION']):
			dg_list.append(tuple((ID, name)))

		self.fields['dg'] = forms.ChoiceField(
			required=False,
			choices=dg_list,
			label='Disease Grade',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		# disease stage
		disease_stage_list = list()
		disease_stage = json.loads(rora.disease_stage_data()[0])

		for ID, name in zip(disease_stage[0]['DISEASE_STAGE_ID'], disease_stage[1]['DESCRIPTION']):
			disease_stage_list.append(tuple((ID, name)))

		self.fields['disease_stage'] = forms.ChoiceField(
			required=False,
			choices=disease_stage_list,
			label='Disease Stage',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		# read out
		read_out_list = list()
		read_out = json.loads(rora.read_out_data()[0])

		for ID, name in zip(read_out[0]['SCREEN_READOUT_ID'], read_out[1]['DESCRIPTION']):
			read_out_list.append(tuple((ID, name)))

		self.fields['read_out'] = forms.ChoiceField(
			required=False,
			choices=read_out_list,
			label='Screen Read Out',  # initial=organism_list[0][0],
			widget=forms.Select(
				attrs={'class': 'multiselect', }
			)
		)

		# create date

		self.fields['createdate'] = forms.DateField(
			label='Create Date',
			widget=widgets.AdminDateWidget(),
			initial=datetime.date.today()
		)


class ScreenGroup(forms.Form):
	name = forms.CharField(
		max_length=75,
		label="Group Name",
		widget=forms.TextInput(attrs={'placeholder': 'Group Name'})  # required=True
	)


class LoginForm(forms.Form):
	user_name = forms.CharField(
		max_length=30,
		label="",
		widget=forms.TextInput(
			attrs={
				'placeholder': 'user name...',
				'class': 'input-medium',
			}),
	)
	password = forms.CharField(
		max_length=30,
		label="",
		widget=forms.PasswordInput(attrs={
			'placeholder': 'password...',
			'class': 'input-small',
		})
	)


class NewScriptDialog(forms.Form):
	name = forms.CharField(
		max_length=35,
		required=True,
		label=u'Script Name'
	)
	
	category = forms.ModelChoiceField(
		queryset=breeze.models.ScriptCategories.objects.all(),
		empty_label="Please select one ..."
	)

	inline = forms.CharField(
		max_length=150,
		label=u"Inline Description",
		widget=forms.Textarea(
			attrs={
				'class': 'input-large',
				'rows': 1
			}),
	)

	def clean_name(self):
		name = self.cleaned_data['name']
		try:
			breeze.models.Rscripts.objects.get(name=name)
		except breeze.models.Rscripts.DoesNotExist:
			return name
		else:
			raise forms.ValidationError(u"That script name is already taken.")


class NewRepTypeDialog(forms.ModelForm):
	class Meta(object):
		model = breeze.models.ReportType
		fields = ('type', 'description', 'search', 'access', 'manual')
		# widgets = {'access': forms.CheckboxSelectMultiple( attrs = {'class': 'multiselect', })}


class BasicJobForm(forms.Form):
	def __init__(self, user, edit, *args, **kwargs):
		self._user = user
		self._edit = edit
		super(BasicJobForm, self).__init__(*args, **kwargs)

	job_name = forms.CharField(
		max_length=35,
	)
	job_details = forms.CharField(
		widget=forms.Textarea(attrs={'cols': 15, 'rows': 2, 'placeholder': 'optional'}),
		required=False
	)
	report_to = forms.EmailField(
		widget=forms.TextInput(attrs={'placeholder': u'first.last@helsinki.fi'}),
		max_length=75
	)

	def clean_job_name(self):
		job_name = self.cleaned_data.get('job_name')
		try:
			exst = breeze.models.Jobs.objects.filter(juser__exact=self._user).get(jname=job_name).name
		except breeze.models.Jobs.DoesNotExist:
			return job_name
		else:
			if str(exst) == str(self._edit):
				return job_name
			else:
				raise forms.ValidationError(u"That job name already exists.")


class CustomForm(forms.Form):
	def set_fields(self, kwds):
		keys = kwds.keys()
		keys.sort()
		for k in keys:
			self.fields[k] = kwds[k]

	def get(self, k, d=None):
		return self.__dict__.get(k, d)


# ## Forms for script submissions ###
class ScriptBasics(forms.Form):
	def __init__(self, edit, *args, **kwargs):
		self._edit = edit
		super(ScriptBasics, self).__init__(*args, **kwargs)

	name = forms.CharField(
		max_length=35,
		widget=forms.TextInput(
			attrs={
				'class': 'input-large',
			}),
	)

	inline = forms.CharField(
		max_length=150,
		label="Inline Description",
		widget=forms.Textarea(
			attrs={
				'class': 'input-xxlarge',
				'rows': 3
			}),
	)

	def clean_name(self):
		name = self.cleaned_data['name']
		try:
			exst = breeze.models.Rscripts.objects.get(name=name)
		except breeze.models.Rscripts.DoesNotExist:
			return name
		else:
			if str(exst) == str(self._edit):
				return name
			else:
				raise forms.ValidationError("That script name is already taken.")


class ScriptDescription(forms.Form):
	description = forms.CharField(
		max_length=5500,
		label="",
		widget=forms.Textarea(
			attrs={
				'class': 'input-xxlarge',
				'rows': 11
			}),
	)


class ScriptAttributes(forms.ModelForm):
	class Meta(object):
		model = breeze.models.Rscripts
		fields = ('author', 'category', 'draft', 'istag', 'report_type')


class ScriptLogo(forms.Form):
	logo = forms.FileField(label=(u''))


# ## old implementation ###
class ScriptMainForm(forms.ModelForm):
	class Meta(object):
		model = breeze.models.Rscripts
		fields = ('name', 'inln', 'category', 'details', 'logo')


class ScriptSources(forms.Form):
	code = forms.FileField()
	header = forms.CharField(
		widget=forms.Textarea(attrs={'cols': 55, 'rows': 15, }),
		help_text='Header',
	)


class AddBasic(forms.Form):
	TYPE_OPT = (
		(u'NUM', u'Numeric'),
		(u'CHB', u'Check Box'),
		(u'DRP', u'Drop Down'),
		(u'RAD', u'Radio'),
		(u'TEX', u'Text'),
		(u'TAR', u'Text Area'),
		(u'FIL', u'File Upload'),
		(u'HED', u'Heading'),
	)

	def drop_titles(self, *args, **kwargs):
		self.fields['inline_var'].label = ""
		self.fields['comment'].label = ""

	inline_var = forms.CharField(max_length=35,
		widget=forms.TextInput(attrs={'class': 'input-mini'})
	)
	type = forms.CharField(widget=forms.HiddenInput(), required=False)
	comment = forms.CharField(max_length=55,
		widget=forms.TextInput(attrs={'class': 'input-xlarge'})
	)


# default = forms.CharField(max_length=35,
#        widget=forms.TextInput(attrs={'class': 'input-mini'}),
#        required=False
#        )

class AddOptions(forms.Form):
	def drop_titles(self, *args, **kwargs):
		self.fields['options'].label = ""

	options = forms.CharField(max_length=55, widget=forms.TextInput(attrs={'class': 'input-xlarge'}))


class AddDatasetSelect(forms.Form):
	options = forms.ModelMultipleChoiceField(queryset=breeze.models.DataSet.objects.all(),
		widget=forms.CheckboxSelectMultiple())


class AddTemplateInput(forms.Form):
	"""
		This control is for uploading template
		inpit file which can be downloaded from BREEZE beforehand
	"""
	options = forms.ModelChoiceField(queryset=breeze.models.InputTemplate.objects.all())


class HiddenForm(forms.Form):
	next = forms.CharField(widget=forms.HiddenInput())
	curr = forms.CharField(widget=forms.HiddenInput())


def xml_from_form(form_g, form_d, form_s):
	root = Xml.Element('rScript')
	root.attrib['name'] = form_g.cleaned_data['name']
	inline = Xml.Element('inline')
	inline.text = form_g.cleaned_data['inln']
	root.append(inline)
	details = Xml.Element('details')
	details.text = form_g.cleaned_data['details']
	root.append(details)
	status = Xml.Element('status')
	status.attrib['val'] = 'none'
	root.append(status)
	input_array = Xml.Element('inputArray')

	for key in form_d:
		common_form = form_d[key][0]
		ipt = Xml.Element('inputItem')
		ipt.attrib['type'] = common_form.cleaned_data['type']
		ipt.attrib['rvarname'] = common_form.cleaned_data['inline_var']
		ipt.attrib['comment'] = common_form.cleaned_data['comment']
		ipt.attrib['val'] = ""

		if common_form.cleaned_data['type'] == 'TPL':
			extra_form = form_d[key][1]
			ipt.attrib['default'] = str(extra_form.cleaned_data['options'])
		else:
			ipt.attrib['default'] = ""

		if common_form.cleaned_data['type'] == 'DRP' or common_form.cleaned_data['type'] == 'RAD':
			extra_form = form_d[key][1]  # [0] form is the common one
			altar = Xml.Element('altArray')
			for opt in str(extra_form.cleaned_data['options']).split():
				alt_item = Xml.Element('altItem')
				alt_item.text = opt
				altar.append(alt_item)
			ipt.append(altar)

		if common_form.cleaned_data['type'] == 'DTS':
			extra_form = form_d[key][1]
			altar = Xml.Element('altArray')
			for opt in extra_form.cleaned_data['options']:
				alt_item = Xml.Element('altItem')
				alt_item.text = str(opt)
				altar.append(alt_item)
			ipt.append(altar)

		input_array.append(ipt)

	root.append(input_array)

	# new_xml = open("/home/comrade/Projects/fimm/tmp/test.xml", 'w')
	new_xml = open(str(settings.TEMP_FOLDER) + 'test.xml', 'w')
	Xml.ElementTree(root).write(new_xml)
	new_xml.close()
	return new_xml


def form_from_xml(xml_parser, req=None, init=False, usr=None, post=None, files=None, path=None):
	input_array = xml_parser.getroot().find('inputArray')

	if req:
		custom_form = CustomForm(req.POST, req.FILES)
	elif init and post:
		custom_form = CustomForm(post, files)
	else:
		custom_form = CustomForm()

	if input_array is not None:
		for input_item in input_array:
			if input_item.tag == "inputItem":
				try:
					if input_item.attrib["optional"] == '1':
						optional_prop = False
					else:
						optional_prop = True
				except:
					optional_prop = True

				try:
					help_line = input_item.attrib["help"] or ''
					if help_line == 'undefined':
						help_line = ''
				except:
					help_line = ''

				field = None

				if input_item.attrib["type"] == "NUM":  # numeric input
					# protect empty MAX and MIN limits
					if input_item.attrib["max"]:
						max_decimal = Decimal(input_item.attrib["max"])
					else:
						max_decimal = None

					if input_item.attrib["min"]:
						min_decimal = Decimal(input_item.attrib["min"])
					else:
						min_decimal = None

					field = forms.DecimalField(
						initial=input_item.attrib["val"],
						max_value=max_decimal,
						min_value=min_decimal,
						required=optional_prop,
						help_text=help_line
					)

				elif input_item.attrib["type"] == "TEX":  # text box
					field = forms.CharField(
						initial=input_item.attrib["val"],
						max_length=100,
						required=optional_prop,
						help_text=help_line,
						widget=forms.TextInput(attrs={'type': 'text', })
					)
				elif input_item.attrib["type"] == "TAR":  # text area
					field = forms.CharField(
						initial=input_item.attrib["val"],
						required=optional_prop,
						help_text=help_line,
						widget=forms.Textarea(
							attrs={
								'cols': 15,
								'rows': 3,
							}
						)
					)

				elif input_item.attrib["type"] == "CHB":  # check box
					checked = False
					if input_item.attrib["val"] == "true":
						checked = True
					field = forms.BooleanField(
						required=False,
						initial=checked,
						help_text=help_line
					)

				elif input_item.attrib["type"] == "DRP":  # drop down list
					drop_options = tuple()

					for alt in input_item.find('altArray').findall('altItem'):
						drop_options = drop_options + ((alt.text, alt.text),)

					field = forms.ChoiceField(
						choices=drop_options,
						initial=input_item.attrib["val"],
						help_text=help_line
					)

				elif input_item.attrib["type"] == "DTS":  # custom dataset (drop down list control)
					drop_options = tuple()

					for alt in input_item.find('altArray').findall('altItem'):
						drop_options = drop_options + ((alt.text, alt.text),)

					field = forms.ChoiceField(
						choices=drop_options,
						initial=input_item.attrib["val"],
						help_text=help_line
					)

				elif input_item.attrib["type"] == "RAD":  # radio buttons
					radio_options = tuple()

					for alt in input_item.find('altArray').findall('altItem'):
						radio_options = radio_options + ((alt.text, alt.text),)

					field = forms.ChoiceField(
						initial=input_item.attrib["val"],
						widget=forms.RadioSelect(attrs={'value': input_item.attrib["default"]}),
						choices=radio_options,
						help_text=help_line
					)

				elif input_item.attrib["type"] == "FIL" or input_item.attrib["type"] == "TPL":  # file upload field
					# print path, files
					field = forms.FileField(
						# initial=loc
						required=optional_prop,
						help_text=help_line,
						widget=forms.ClearableFileInput(
							attrs={
								'class': input_item.attrib["type"],
								'which': input_item.attrib["default"],
							}
						)
					)
				elif input_item.attrib["type"] == "MLT":  # multiple select
					mult_options = tuple()

					for alt in input_item.find('altArray').findall('altItem'):
						mult_options = mult_options + ((alt.text, alt.text),)

					field = forms.MultipleChoiceField(
						initial=re.split(',', input_item.attrib["val"]),
						help_text=help_line,
						choices=mult_options
					)

				# Dotmatix samples control
				elif input_item.attrib["type"] == "DTM_SAMPLES":  # custom dataset (multiple select)

					# group_list_of_tuples = list()
					# sample_list_of_tuples = list()

					# push r-code here to populate dtm_samples
					group_list_of_tuples = rora.get_dtm_screen_groups()
					sample_list_of_tuples = rora.get_dtm_screens()

					dtm_options = list()
					dtm_options.append(tuple(( 'Groups', tuple(group_list_of_tuples) )))
					dtm_options.append(tuple(( 'Individual Screens', tuple(sample_list_of_tuples) )))

					field = forms.MultipleChoiceField(
						choices=dtm_options,
						initial=input_item.attrib["val"],
						required=optional_prop,
						help_text=help_line,
						widget=forms.SelectMultiple(attrs={'class': 'dotmatix_samples'})
					)

				elif input_item.attrib["type"] == "SCREEN_GROUPS":
					# group_list_of_tuples = list()

					group_list_of_tuples = rora.get_dtm_screen_groups()

					dtm_options = list()
					dtm_options.append(tuple(( 'Groups', tuple(group_list_of_tuples) )))

					field = forms.MultipleChoiceField(
						choices=dtm_options,
						initial=input_item.attrib["val"],
						required=optional_prop,
						help_text=help_line,
						widget=forms.SelectMultiple(attrs={'class': 'dotmatix_samples'})
					)

				elif input_item.attrib["type"] == "HED":  # section header
					pass
				else:
					pass

				if field:
					custom_form.fields[input_item.attrib["comment"]] = field
			elif input_item.tag == "subSection":
				print "section"
			else:
				pass

	return custom_form


def create_report_sections(sections, req=None, posted=None, files=None, path=None):
	"""
	Creates a list of sections content for report overview page.

	:param sections:  list of 'Rscripts' db objects
	:type sections: list
	:type req:
	:type posted: dict
	:type files:
	:type path:
	:rtype: list
	"""
	sdata = dict()
	section_lst = list()

	for item in sections:
		if item.is_valid():
			tree = Xml.parse(item.xml_path)
		else:
			tree = Xml.parse(settings.NO_TAG_XML)
			sdata['isvalid'] = False
		sdata['id'] = item.id
		key = 'Section_dbID_' + str(item.id)
		sdata['value'] = posted[key] if posted and key in posted else 0
		sdata['inline'] = str(item.inln)
		sdata['name'] = str(item.name)
		sdata['form'] = form_from_xml(
			xml_parser=tree, post=posted, files=files, usr=req.user, init=True if posted else False, path=path)
		sdata['size'] = len(sdata['form'].__str__())
		section_lst.append(dict(sdata))

	return section_lst


def validate_report_sections(sections, req):
	""" Validate only checked (marked) report sections.

	Arguments:
	:param sections:  list of 'Rscripts' db objects
	:type sections: list
	:param req:  a copy of request
	:type req:
	:rtype: list
	"""
	s_data = dict()
	section_lst = list()

	for item in sections:
		if item.is_valid():
			tree = Xml.parse(item.xml_path)
			s_data['id'] = item.id
			s_data['inline'] = str(item.inln)
			s_data['name'] = str(item.name)

			# we want to validate only those sections
			# that have been enabled by user
			section_id = 'Section_dbID_' + str(item.id)
			if section_id in req.POST and req.POST[section_id] == '1':
				s_data['form'] = form_from_xml(xml_parser=tree, req=req, usr=req.user)
				s_data['isvalid'] = s_data['form'].is_valid()
			else:
				s_data['form'] = form_from_xml(xml_parser=tree, usr=req.user)
				s_data['isvalid'] = True
			section_lst.append(dict(s_data))

	return section_lst


def check_validity(sections):
	""" Reports whether all sections are valid or not

	Arguments:
	:param sections: a list of dict()
	:type sections: list
	:rtype: bool
	"""
	for item in sections:
		if not item['isvalid']:
			return False

	return True


def job_summary(_):
	pass
