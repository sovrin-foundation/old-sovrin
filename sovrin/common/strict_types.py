"""
Thanks to Ilya Peterov for the base code from
https://github.com/ipeterov/strict_types.
"""

if 'defaultShouldCheck' not in globals():
    defaultShouldCheck = False

import inspect

from typing import get_type_hints


class strict_types:

    def __init__(self, shouldCheck=None):
        if shouldCheck is not None:
            self.shouldCheck = shouldCheck
        else:
            self.shouldCheck = defaultShouldCheck

    def __call__(self, function):

        if not self.shouldCheck:
            return function

        hints = get_type_hints(function)

        def precheck(*args, **kwargs):

            all_args = kwargs.copy()
            all_args.update(dict(zip(function.__code__.co_varnames, args)))

            for argument, argument_type in ((i, type(j)) for i, j in all_args.items()):
                if argument in hints:
                    if not issubclass(argument_type, hints[argument]):
                        raise TypeError('Type of {} is {} and not {}'.
                                        format(argument,
                                               argument_type,
                                               hints[argument]))

        def postcheck(result):
            if 'return' in hints:
                if not isinstance(result, hints['return']):
                    raise TypeError('Type of result is {} and not {}'.
                                    format(type(result), hints['return']))
            return result

        if inspect.iscoroutinefunction(function):
            async def type_checker(*args, **kwargs):
                precheck(*args, **kwargs)
                result = await function(*args, **kwargs)
                return postcheck(result)
        else:
            def type_checker(*args, **kwargs):
                precheck(*args, **kwargs)
                result = function(*args, **kwargs)
                return postcheck(result)

        return type_checker


def decClassMethods(decorator):
    def decClass(cls):
        for name, m in inspect.getmembers(cls, inspect.isfunction):
            setattr(cls, name, decorator(m))
        return cls
    return decClass
