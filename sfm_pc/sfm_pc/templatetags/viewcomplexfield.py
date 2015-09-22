from django.template import Library

register = Library()

@register.inclusion_tag('complexfield/view.html')
def view_complex_field(field, object_id, path):
    if isinstance(field, str):
        raise Exception("Can't render field: field is str")
    field_id = field.get_field_str_id()
    if object_id is None:
        object_id = 0

    return {
        'value' : field,
        'object_id': object_id,
        'object_name': field.get_object_name(),
        'field_str_id': field.get_field_str_id(),
        'attr_name': field.get_attr_name(),
        'field_id': field_id,
        'field_name': field.field_name,
        'sourced': field.sourced,
        'translated': field.translated,
        'versioned': field.versioned,
        'path': path,
    }
