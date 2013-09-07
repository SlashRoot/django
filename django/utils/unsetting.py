from functools import wraps, update_wrapper
import inspect

from django.conf import settings

"""
This is an incremental project to remove settings dependencies from Django
libraries so that Django core libraries can be imported without a settings
file or initialization.
"""

OVERWRITE_SENTINEL = 'FAKE_VALUE'

class SettingDetails():
    def __init__(self, setting, setting_details, arg_names):
        self.setting = setting
        setting_list = (list(setting_details)
                        if isinstance(setting_details, (list, tuple))
                        else [setting_details])
        self.arg = setting_list[0]
        self.fallback_trigger_value = (setting_list[1] 
                                  if len(setting_list) > 1
                                  else OVERWRITE_SENTINEL)
        try:
            self.index = arg_names.index(self.arg)
        except ValueError:
            self.index = None

    def __repr__(self):
        return str([self.arg, self.index, self.fallback_trigger_value])


def uses_settings(setting_name_or_dict, kw_arg=None, fallback_trigger_value=OVERWRITE_SENTINEL):
    """
    Decorator for functions
    :param setting_name_or_dict: setting attribute, e.g. 'USE_TZ'.  
                  Alternatively, you can send in a dict like {'USE_TZ': ['use_tz', None]}
                  where the None value is an optionally set fallback_trigger_value per setting key
    :param kw_arg: function parameter that can be used instead of the setting
    :param fallback_trigger_value: In some cases, explicitly setting the parameter
                  should still use the settings attribute, especially when
                  there was an existing required parameter
    """
    def _dec(func):
        setting_map = {}
        arg_names = inspect.getargspec(func).args

        # http://stackoverflow.com/questions/8793233/python-can-a-decorator-determine-if-a-function-is-being-defined-inside-a-class
        frames = inspect.stack()
        defined_in_class = False
        if len(frames) > 2:
            maybe_class_frame = frames[2]
            statement_list = maybe_class_frame[4]
            first_statment = statement_list[0]
            if first_statment.strip().startswith('class '):
                defined_in_class = True

        func.first_arg_name = arg_names.pop(0) if defined_in_class else None

        kw_defaults = inspect.getargspec(func).defaults
        if isinstance(setting_name_or_dict, dict):
            for k,v in setting_name_or_dict.items():
                details = SettingDetails(k, v, arg_names)
                setting_map[details.arg] = details
        else: #it should be a string
            if kw_arg is None:
                raise TypeError("required kw_arg argument")
            setting_map[kw_arg] = SettingDetails(
                setting_name_or_dict, [kw_arg, fallback_trigger_value],
                arg_names)

        def _wrapper(*args, **kwargs):
            new_kwargs = kwargs.copy()

            # If we have set a first_arg_name for the function, we know it's a method
            # We need to re-apply that arg here.
            if func.first_arg_name:
                args = list(args)  # args will need to be mutable...
                new_kwargs[func.first_arg_name] = args.pop(0) # So that we can pop the self off.

            max_args_index = 1000
            for counter, arg in enumerate(arg_names):
                try:
                    # First, see if it is set positionally...
                    new_kwargs[arg] = args[counter]
                    max_args_index = min(max_args_index, counter)
                except IndexError:
                    if not kwargs.has_key(arg):
                        if arg in setting_map:
                            new_kwargs[arg] = getattr(settings,
                                                      setting_map[arg].setting)
                        else:
                            position = len(args) - counter
                            new_kwargs[arg] = kw_defaults[position]

                if setting_map.has_key(arg) \
                        and new_kwargs[arg] == setting_map[arg].fallback_trigger_value:
                    new_kwargs[arg] = getattr(settings, setting_map[arg].setting)



            return func(*args[:max_args_index], **new_kwargs)
        update_wrapper(_wrapper, func)
        return _wrapper
    return _dec

