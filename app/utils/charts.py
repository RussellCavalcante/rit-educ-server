
def get_new_line_chart(labels=[], datasets=[], title=''):
    return {
        'type': 'line',
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'options': {
            'title': {'display': True, 'text': title},
            'responsive': True,
            'maintainAspectRatio': True,
            #'legend': {'labels': {'fontColor': 'white'}}
        }}
