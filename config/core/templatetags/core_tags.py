from django import template
register = template.Library()

@register.filter
def get_region_drug(dictionary, region_drug):
    try:
        region_name, drug_name = region_drug.split("|")
        return dictionary.get(region_name, {}).get(drug_name, 0)
    except:
        return 0



@register.filter
def get_total_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0
