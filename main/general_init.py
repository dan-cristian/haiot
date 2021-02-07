import threading
from common import fix_module
while True:
    try:
        import wheel  # needed for auto install/compile
        import ujson
        # import requests
        break
    except ImportError as iex:
        if not fix_module(iex):
            break
from common import Constant
from main.logger_helper import L
from main import system_info
import transport
from main import thread_pool



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
    from storage.model import m
    mods = m.Module.find(filter={m.Module.host_name: ''}, sort=[(m.Module.start_order, 1)])
    if len(mods) == 0:
        L.l.error('No modules to initialise')
    else:
        for mod in mods:
            if mod.name != 'main':
                # check if there is a host specific module and use it with priority over generic one
                mod_host_specific = m.Module.find_one({m.Module.host_name: Constant.HOST_NAME, m.Module.name: mod.name})
                if mod_host_specific is not None:
                    mod_name = mod_host_specific.name
                    mod_active = mod_host_specific.active
                    L.l.info("Found specific module init for {}, active={}".format(mod_name, mod_active))
                else:
                    mod_name = mod.name
                    mod_active = mod.active
                    L.l.info("No specific module init found for {}, active={}".format(mod_name, mod_active))
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
        breakpoint()
    except Exception as ex:
        print("Error in remote debug: {}".format(ex))


def _init_debug_pycharm():
    import pydevd_pycharm
    pydevd_pycharm.settrace('192.168.0.105', port=12888, stdoutToServer=True, stderrToServer=True)


def unload():
    L.l.info('Main module is unloading, application will exit')
    import main.thread_pool
    P.shutting_down = True
    main.thread_pool.P.tpool = False
    unload_modules()


def init(arg_list):
    if 'remote_debug' in arg_list:
        # _init_debug()
        _init_debug_pycharm()
        # if Constant.is_os_linux():
        #    from pudb import set_trace
        #    set_trace(paused=False)
    system_info.init()
    # import storage.tiny.tinydb_app
    # storage.tiny.tinydb_app.init(arg_list)
    import storage.model
    storage.model.init(arg_list)
    if 'standalone' not in arg_list:
        transport.init()
    from main import event
    event.init()
    init_modules(init_mod=True)
    init_post_modules()
    t = threading.Thread(target=thread_pool.run_thread_pool)
    t.daemon = True
    t.start()

