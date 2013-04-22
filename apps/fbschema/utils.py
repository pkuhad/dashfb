
def get_fields_from_model(model):
    '''
    Returns a comma separated field names for a particular model
    '''
    # Assumption : model isinstance = django.db.models.Model -> Can be raised an Exception
    # Test Case : 1) function should return string of non zero string
    return ", ".join(get_fieldlist_from_model(model))

def get_fql_from_model(model, clause):
    '''
    Genearates a fql query string with given clause. Clause is the suffix part begining from 'WHERE'
    '''
    return "SELECT %s FROM %s %s" % (get_fields_from_model(model), model.fqlname, clause)


def get_fieldlist_from_model(model):
    '''
    Returns a python list of model fields
    '''
    return [getattr(field, 'name') for field in model._meta.fields if getattr(field, 'name') not in model.ignore_fields]


def compare_keys_with_fields(model, keys):
    '''
    Compares returned data set keys for a particular fql query with the model fields in concern.
    Basically they must be equal because requested keys were generated from model fields 
    '''
    fields = get_fieldlist_from_model(model)
 
    for key in keys:
        if key not in fields:
            return False

    for field in fields:
        if field not in keys:
            return False

    return True

