import threading
from tinydb import Query
import common
from common import Constant
from main.logger_helper import L
from main import system_info
import transport
from main import thread_pool
from common.utils import Struct

class P:
    init_mod_list = []
    shutting_down = False

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
    from tinydb_app import db
    from tinydb_model import Module
    # m = Module.coll.find_one(host_name='')
    m = Module.t.search(Query().host_name == '')
    q2 = Query()
    for mod_dict in m:
        mod = Struct(**mod_dict)
        if mod.name != 'main':
            # check if there is a host specific module and use it with priority over generic one
            mod_host_spec = Module.t.search((q2.host_name == Constant.HOST_NAME) & (q2.name == mod.name))
            if len(mod_host_spec) == 1:
                mod_host_specific = Struct(**mod_host_spec[0])
                mod_name = mod_host_specific.name
                mod_active = mod_host_specific.active
            elif len(mod_host_spec) == 0:
                mod_name = mod.name
                mod_active = mod.active
            else:
                L.l.warning('Unexpected nr of modules for {} host {}'.format(mod.name, Constant.HOST_NAME))
                break
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


def _init_debug():
    try:
        import ptvsd
        ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
        print('Enabled remote debugging, waiting 15 seconds for client to attach')
        ptvsd.wait_for_attach(timeout=15)
    except Exception as ex:
        print("Error in remote debug: {}".format(ex))


def unload():
    L.l.info('Main module is unloading, application will exit')
    import main.thread_pool
    P.shutting_down = True
    main.thread_pool.P.tpool = False
    unload_modules()


def init(arg_list):
    L.init_logging()
    common.load_config_json()
    common.init_simple()
    if 'debug_remote' in arg_list:
        _init_debug()
    system_info.init()
    common.init()
    import flask_app
    import main.tinydb_app
    main.tinydb_app.init(arg_list)
    if 'standalone' not in arg_list:
        transport.init()
    t = threading.Thread(target=thread_pool.run_thread_pool)
    t.daemon = True
    t.start()
    init_modules(init_mod=True)
    init_post_modules()

