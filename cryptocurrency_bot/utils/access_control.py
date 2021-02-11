def accessControl(type_, failIf):
    def onDecorator(aClass):
        class onInstance:
            def __init__(self, *args, **kargs):
                self.__wrapped = aClass(*args, **kargs)

            def __getattr__(self, attr):
                if failIf(attr) and 'get' in type_:
                    raise TypeError('private attribute fetch: ' + attr)
                else:
                    return getattr(self.__wrapped, attr)

            def __setattr__(self, attr, value):
                if attr == '_onInstance__wrapped':
                    self.__dict__[attr] = value
                elif failIf(attr) and 'set' in type_:
                    raise TypeError('private attribute change: ' + attr)
                else:
                    setattr(self.__wrapped, attr, value)
        return onInstance
    return onDecorator



def private(types:list=['get', 'set'], *attributes):
    return accessControl(types, failIf=(lambda attr: attr in attributes))
 
def public(types:list=['get', 'set'], *attributes):
    return accessControl(types, failIf=(lambda attr: attr not in attributes))
