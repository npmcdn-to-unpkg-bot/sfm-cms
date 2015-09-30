import inspect
import reversion
import re

from django.db import models
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError, FieldDoesNotExist
from django.utils.translation import get_language

from languages_plus.models import Language

from source.models import Source
from translation.models import get_language_from_iso
from sfm_pc.utils import class_for_name


class ComplexField(models.Model):
    lang = models.CharField(max_length=5, null=True)
    sources = models.ManyToManyField(Source, related_name="%(app_label)s_%(class)s_related")

    class Meta:
        abstract = True

    def revert(self, id):
        if hasattr(self, 'versioned'):
            version = reversion.get_for_object(self).get(id=id)
            version.revert()
            return version.field_dict['sources']

    def revert_to_source(self, source_ids):
        if hasattr(self, 'versioned'):
            versions = reversion.get_for_object(self)
            version = None
            max_id = 0
            for vers in versions:
                if vers.field_dict['sources'] == source_ids and vers.id > max_id:
                    version = vers
                    max_id = vers.id

            if version is None:
                for vers in versions:
                    if vers.field_dict['sources'] == [] and vers.id > max_id:
                        version = vers

            if version is not None:
                try:
                    version.revert()
                except IntegrityError:
                    # The original object of this version has been deleted,
                    # we ignore it.
                    pass

class ComplexFieldContainer(object):
    def __init__(self, table_object, field_model, id_=None):
        self.table_object = table_object
        self.field_model = field_model
        self.sourced = hasattr(field_model(), 'sourced')
        self.translated = hasattr(field_model(), 'translated')
        self.versioned = hasattr(field_model(), 'versioned')
        self.id_ = id_

    def __str__(self):
        value = self.get_value(get_language())
        if value is None:
            value = ""
        return value

    @property
    def field_name(self):
        if self.id_ is None:
            if not hasattr(self.field_model(),'field_name'):
                return 'No field model'
            return self.field_model().field_name

        try:
            field = self.field_model.objects.get(pk=self.id_)
            return field.field_name
        except self.field_model.DoesNotExist:
            if not hasattr(self.field_model(),'field_name'):
                return 'No field model'
            return self.field_model().field_name

    def get_attr_name(self):
        table_name = self.table_object.__class__.__name__
        return re.sub(table_name, '', self.field_model.__name__).lower()

    def get_object_id(self):
        if self.table_object.id:
            return self.table_object.id
        else:
            return None

    def get_object_name(self):
        return self.table_object.__class__.__name__.lower()

    def get_field_str_id(self):
        table_name = self.table_object.__class__.__name__
        field_name = self.field_model.__name__
        return table_name + "_" + field_name

    def get_field(self, lang=get_language()):
        if self.id_ == 0:
            return None

        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        if self.id_:
            c_fields = c_fields.filter(pk=self.id_)

        if self.translated:
            c_fields_lang = c_fields.filter(lang=lang)
            c_field = list(c_fields_lang[:1])

            if not c_field:
                c_fields = c_fields.filter(lang='en')
                c_field = list(c_fields[:1])
        else:
            c_field = list(c_fields[:1])

        if c_field:
            return c_field[0]

        return None

    def get_value(self, lang=get_language()):
        field = self.get_field(lang)
        if field is not None:
            return field.value
        return None

    def set_value(self, value, lang=get_language()):
        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        if self.translated:
            c_fields = c_fields.filter(lang=lang)
        field = list(c_fields[:1])
        if field:
            field[0].value = value
            field[0].save()
        else:
            new_field = self.field_model()
            if self.translated:
                new_field.lang = lang
            new_field.value = value
            new_field.save()

    def get_history(self):
        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        history = {}
        for c_field in c_fields:
            field_history = reversion.get_for_object(c_field)
            history[c_field.lang] = [
                {
                    "value": str(fh.field_dict['value']),
                    "sources": fh.field_dict['sources'],
                    "id": fh.id
                }
                for fh in field_history
            ]
        return history

    def get_history_for_lang(self, lang=get_language()):
        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        c_fields = c_fields.filter(lang=lang)
        history = []
        field = list(c_fields[:1])
        if field:
            field_history = reversion.get_for_object(field[0])
            history = [
                {
                    "value": fh.field_dict['value'],
                    "sources": [
                        {"source": src.source, "confidence": src.confidence}
                        for src in Source.get_sources(fh.field_dict['sources'])
                    ],
                    "id": fh.id
                }
                for fh in field_history
            ]

        return history

    def get_langs_in_history(self):
        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        langs = []
        if c_fields:
            langs = [
                {
                    "label": get_language_from_iso(field.lang),
                    "value": field.lang
                }
                for field in c_fields
            ]

        return langs

    def get_translations(self):
        translations = []
        if not hasattr(self.field_model, 'translated'):
            return translations

        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        c_fields = c_fields.exclude(value__isnull=True).exclude(value__exact='')

        for field in c_fields:
            trans = {
                'lang': get_language_from_iso(field.lang),
                'value': field.value
            }
            translations.append(trans)

        return translations

    def revert_field(self, lang, id_):
        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        c_fields = c_fields.filter(lang=lang)
        field = list(c_fields[:1])
        if field:
            sources = field[0].sources.all()
            field[0].revert(id_)

            fields = self.field_model.objects.filter(object_ref=self.table_object)
            fields = fields.exclude(lang = lang)
            for field in fields:
                field.revert_to_source(sources)

    def get_sources(self):
        sources = []
        if not hasattr(self.field_model, 'sourced'):
            return sources

        c_fields = self.field_model.objects.filter(object_ref=self.table_object)
        field = list(c_fields[:1])
        if field:
            sources = field[0].sources.all()

        return sources


    def update(self, value, lang, sources=[]):
        c_field = self.get_field(lang)
        sources_updated = False

        c_fields = self.field_model.objects.filter(object_ref=self.table_object)

        # Update translations
        for field in c_fields:
            # Set translation values to None if the value is changed
            if c_field is None or c_field.value != value:
                field.value = None

            # Update sources for all translations if they are not the same
            if self.sourced and not self.has_same_sources(sources):
                sources_updated = True
                field.sources.clear()
                for source in sources:
                    field.sources.add(source)
            if field.lang != lang:
                field.save()

        if c_field is None:
            if self.translated:
                c_field = self.field_model(object_ref=self.table_object, lang=lang)
                c_field.save()
                if self.sourced:
                    sources_updated = True
                    for source in sources:
                        c_field.sources.add(source)
            else:
                c_field = self.field_model(object_ref=self.table_object)

        # New version only if there was a change on this field
        if c_field.value != value or sources_updated:
            c_field.value = value
            c_field.save()

    def translate(self, value, lang):
        c_fields = self.field_model.objects.filter(object_ref=self.table_object)

        if not c_fields.exists():
            raise FieldDoesNotExist("Can't translate a field that doesn't exist")

        c_field = c_fields.filter(lang=lang)
        c_field = list(c_field[:1])
        if not c_field:
            c_field = self.field_model(object_ref=self.table_object, lang=lang)
        else:
            c_field = c_field[0]
            if c_field.value != None:
                raise ValidationError("Can't translate an already translated field")

        c_field.value = value
        c_field.save()

        if hasattr(c_field, 'sourced'):
            with_sources = c_fields.exclude(sources=None)
            sources = with_sources[0].sources.all()
            for src in sources:
                c_field.sources.add(src)

        c_field.save()

    def validate(self, value, lang, sources=[]):
        if hasattr(self.field_model(), "source_required"):
            if not len(sources):
                return ("Sources are required to update this field", value)

        fk_model = self.get_fk_model()
        if fk_model is not None:
            try:
                value = fk_model.objects.get(pk=value)
            except fk_model.DoesNotExist:
                return (_("The object does not exists"), value)

        return (None, value)

    def get_fk_model(self, field_name="value"):
        field_object, model, direct, m2m = (
            self.field_model._meta.get_field_by_name(field_name)
        )
        if not m2m and direct and isinstance(field_object, models.ForeignKey):
            return field_object.rel.to
        return None


    def has_same_sources(self, sources):
        saved_sources = []
        for src in self.get_sources():
            saved_src = {}
            saved_src['source'] = src.source
            saved_src['confidence'] = src.confidence
            saved_sources.append(saved_src)
        pairs = zip(saved_sources, sources)
        if len(saved_sources) != len(sources) or any(x != y for x, y in pairs):
            return False
        return True

    @classmethod
    def field_from_str_and_id(cls, object_name, object_id, field_name, field_id=None):
        object_class = class_for_name(
            object_name.capitalize(),
            object_name + ".models"
        )

        if object_id == '0':
            object_ = object_class()
        else:
            object_ = object_class.from_id(object_id)
        field = getattr(object_, field_name)

        if isinstance(field, ComplexFieldListContainer):
            container = ComplexFieldListContainer(field.table_object, field.field_model)
            field = container.get_complex_field(field_id)

        return field


class ComplexFieldListContainer(object):
    def __init__(self, table_object, field_model):
        self.table_object = table_object
        self.field_model = field_model

    def get_list(self):
        complex_fields = []
        try:
            fields = self.field_model.objects.filter(object_ref=self.table_object).order_by("value")
        except self.field_model.DoesNotExist:
            return []
        for field in fields:
            complex_fields.append(
                ComplexFieldContainer(self.table_object, self.field_model, field.id)
            )

        return complex_fields

    def get_complex_field(self, id_):
        try:
            field = ComplexFieldContainer(self.table_object, self.field_model, id_)
            return field
        except self.field_model.DoesNotExist:
            return None
