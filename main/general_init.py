from main.logger_helper import L
import common
from common import Constant


class P:
    init_mod_list = []

    def __init__(self):
        pass


def my_import(name):
    # http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    try:
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod
    except Exception as ex:
        L.l.error("Unable to import module {}, err={}".format(name, ex), exc_info=True)
        return None


def init_module(module_name, module_is_active):
    if module_is_active:
        # L.l.info("Importing module {}".format(module_name))
        dynclass = my_import(module_name)
        if dynclass:
            # Log.logger.info('Module {} is marked as active'.format(module_name))
            if hasattr(dynclass, 'initialised'):
                inited = dynclass.initialised
            else:
                inited = dynclass.P.initialised
            if not inited:
                L.l.info('Module {} initialising'.format(module_name))
                dynclass.init()
                P.init_mod_list.append(module_name)
            else:
                L.l.info('Module {} already initialised, skipping init'.format(module_name))
        else:
            L.l.critical("Module {} failed to load".format(module_name))
    else:
        L.l.info("Module {} is marked as not active, skipping load".format(module_name))
        '''    if dynclass.initialised:
                Log.logger.info('Module {} has been deactivated, unloading'.format(module_name))
                dynclass.unload()
                del dynclass
            else:
                Log.logger.info('Module {} already disabled, skipping unload'.format(module_name))
        '''


def unload_module(module_name):
    dynclass = my_import(module_name)
    if dynclass:
        try:
            if hasattr(dynclass, 'initialised'):
                inited = dynclass.initialised
            else:
                inited = dynclass.P.initialised
            if inited:
                L.l.info('Module {} unloading'.format(module_name))
                dynclass.unload()
            else:
                L.l.info('Module {} is not initialised, skipping unload'.format(module_name))
        except Exception as ex:
            L.l.info("Error unloading module {}, ex={}".format(module_name, ex))


def init_modules(init_mod=None):
    m = admin.models.Module
    # http://docs.sqlalchemy.org/en/rel_0_9/core/sqlelement.html
    # keep host name default to '' rather than None (which does not work on filter in)
    # get the unique/distinct list of all modules defined in config, generic or host specific ones
    module_list = m.query.filter(m.host_name.in_([Constant.HOST_NAME, ""])).group_by(m.start_order).all()
    for mod in module_list:
        # Log.logger.info("Processing host specific module definition {} {}".format(mod.name, mod.active))
        assert isinstance(mod, admin.models.Module)
        if mod.name != 'main':
            # check if there is a host specific module and use it with priority over generic one
            mod_host_specific = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.name.in_([mod.name]))
            # mod_host_specific = m.query.filter(m.host_name.in_([constant.HOST_NAME]), m.name.in_([mod.name]))
            if mod_host_specific:
                # Log.logger.info("Initialising host specific module definition {} {}".format(
                #    mod_host_specific.name, mod_host_specific.active))
                mod_name = mod_host_specific.name
                mod_active = mod_host_specific.active
            else:
                # Log.logger.info("Initialising generic mod definition name={} active={}".format(mod.name, mod.active))
                mod_name = mod.name
                mod_active = mod.active
            if init_mod is True:
                init_module(mod_name, mod_active)
            elif init_mod is False and mod_active is True:
                unload_module(mod_name)


def init_post_modules():
    # run post_init actions
    for module_name in P.init_mod_list:
        dynclass = my_import(module_name)
        if dynclass:
            # Log.logger.info('Module {} is marked as active'.format(module_name))
            if hasattr(dynclass, 'initialised'):
                inited = dynclass.initialised
            else:
                inited = dynclass.P.initialised
            if inited and hasattr(dynclass, 'post_init'):
                dynclass.post_init()


def unload_modules():
    init_modules(init_mod=False)


def unload():
    L.l.info('Main module is unloading, application will exit')
    import main.thread_pool

    global shutting_down
    shutting_down = True
    main.thread_pool.P.tpool = False
    unload_modules()


def init():
    L.init_logging()
    common.load_config_json()
