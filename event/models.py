from django.contrib.gis.db import models
from django.utils.translation import ugettext as _
from django.db.models import Max
from django.contrib.gis import geos

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import versioned, translated, sourced, sourced_optional
from complex_fields.models import ComplexField, ComplexFieldContainer, ComplexFieldListContainer
from complex_fields.base_models import BaseModel
from source.models import Source
from person.models import Person
from organization.models import Organization

CONFIDENCE_LEVELS = (
    ('1', _('Low')),
    ('2', _('Medium')),
    ('3', _('High')),
)


class Event(models.Model, BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.startdate = ComplexFieldContainer(self, EventStartDate)
        self.enddate = ComplexFieldContainer(self, EventEndDate)
        self.locationdescription = ComplexFieldContainer(
            self, EventLocationDescription
        )
        self.adminlevel1 = ComplexFieldContainer(self, EventAdminLevel1)
        self.adminlevel2 = ComplexFieldContainer(self, EventAdminLevel2)
        self.geoname = ComplexFieldContainer(self, EventGeoname)
        self.geonameid = ComplexFieldContainer(self, EventGeonameId)
        self.location = ComplexFieldContainer(self, EventLocation)
        self.description = ComplexFieldContainer(self, EventDescription)
        self.perpetrator = ComplexFieldContainer(self, EventPerpetrator)
        self.perpetratororganization = ComplexFieldContainer(
            self, EventPerpetratorOrganization
        )

        self.complex_fields = [self.startdate, self.enddate, self.locationdescription,
                               self.adminlevel1, self.adminlevel2, self.geoname,
                               self.geonameid, self.location, self.description,
                               self.perpetrator, self.perpetratororganization]

        self.required_fields = []

        self.types = ComplexFieldListContainer(self, EventType)

    def validate(self, dict_values):
        errors = {}

        start = dict_values['Event_EventStartDate']
        end = dict_values['Event_EventEndDate']
        if (start and start.get('value') and end and end.get('value') and
                start.get('value') >= end.get('value')):
            errors['Event_EventStartDate'] = _(
                "The start date must be before the end date"
            )

        (base_errors, values) = super().validate(dict_values)
        errors.update(base_errors)

        return (errors, values)

@versioned
@sourced
class EventStartDate(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Start date")

@versioned
@sourced
class EventEndDate(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("End date")


@translated
@versioned
@sourced
class EventLocationDescription(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Location description")

@versioned
@sourced
class EventAdminLevel1(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Admin level 1")

@versioned
@sourced
class EventAdminLevel2(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Admin level 2")

@versioned
@sourced
class EventGeoname(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("GeoName name")

@versioned
@sourced
class EventGeonameId(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("GeoName ID")

@versioned
@sourced
class EventLocation(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.PointField(default=None, blank=True, null=True)
    field_name = _("Location")

@versioned
@sourced
class EventDescription(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Description")

@versioned
@sourced
class EventPerpetrator(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.ForeignKey(Person, default=None, blank=True, null=True)
    field_name = _("Perpetrator")

@versioned
@sourced
class EventPerpetratorOrganization(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.ForeignKey(Organization, default=None, blank=True, null=True)
    field_name = _("Perpetrator Organization")

@versioned
@sourced
class EventType(ComplexField):
    object_ref = models.ForeignKey('Event')
    value = models.ForeignKey('Type', default=None, blank=True, null=True)


class Type(models.Model):
    code = models.TextField()
