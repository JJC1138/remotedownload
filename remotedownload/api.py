__all__ = ['field_keys', 'item_keys', 'encoding']

class StringAttributes():
    def __init__(self, items):
        for i in items:
            setattr(self, i, i)
    def __iter__(self):
        return iter(self.__dict__.keys())

field_keys = StringAttributes([
    'label',
    'referer',
    'folder',
    'headers',
    'cookies',
    'items',
])
field_keys.post_data = 'postData'
field_keys.user_agent = 'userAgent'

item_keys = StringAttributes([
    'url',
    'filename'
])

encoding = 'utf-8'
