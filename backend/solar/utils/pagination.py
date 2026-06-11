from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def apply_date_filters(queryset, params, date_field='date'):
    date_from = params.get('date_from')
    date_to = params.get('date_to')
    if date_from:
        queryset = queryset.filter(**{f'{date_field}__gte': date_from})
    if date_to:
        queryset = queryset.filter(**{f'{date_field}__lte': date_to})
    return queryset


def apply_panel_group_filter(queryset, params):
    panel_group = params.get('panel_group')
    if panel_group:
        queryset = queryset.filter(panel_group_id=panel_group)
    return queryset


def get_date_from_params(params):
    date_from = params.get('date_from')
    date_to = params.get('date_to')
    return date_from, date_to
