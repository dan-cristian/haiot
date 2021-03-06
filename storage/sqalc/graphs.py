__author__ = 'dcristian'


class BaseGraph:
    def __init__(self):
        pass

    save_to_graph = False  # if true this record will be uploaded to a graph
    last_save_to_graph = None  # last date, used to upload with a certain frequency


    @property
    def graph_x_(self):
        pass
        # raise NotImplementedError

    @property
    def graph_y_(self):
        pass
        # raise NotImplementedError

    @property
    def graph_id_(self):
        pass
        # not raising error as some classes can implement basegraph (for simple save to DB history)
        # raise NotImplementedError

    @property
    def graph_legend_(self):
        pass
        # raise NotImplementedError


class SensorGraph(BaseGraph):
    def __init__(self):
        BaseGraph.__init__(self)

    graph_x_ = 'updated_on'
    graph_y_ = ['temperature', 'humidity', 'counters_a', 'counters_b', 'delta_counters_a', 'delta_counters_b',
                'iad', 'vdd', 'vad']
    graph_shape_ = ['spline','spline']
    graph_id_ = 'address'
    graph_legend_ = 'sensor_name'


class SystemMonitorGraph(BaseGraph):
    def __init__(self):
        BaseGraph.__init__(self)

    graph_x_ = 'updated_on'
    graph_y_ = ['cpu_usage_percent', 'memory_available_percent', 'uptime_days', 'cpu_temperature']
    graph_shape_ = ['spline','spline','hv', 'spline']
    graph_id_ = 'name'
    graph_legend_ = 'name'


class SystemDiskGraph(BaseGraph):
    def __init__(self):
        BaseGraph.__init__(self)
    graph_x_ = 'updated_on'
    graph_y_ = ['temperature', 'power_status', 'sector_error_count', 'load_cycle_count', 'start_stop_count',
                'last_reads_elapsed', 'last_writes_elapsed']
    graph_shape_ = ['spline','hv','hv','hv','hv',
                    'hv', 'hv']
    graph_id_ = 'serial'
    graph_legend_ = 'hdd_name'


class NodeGraph(BaseGraph):
    def __init__(self):
        BaseGraph.__init__(self)
    graph_x_ = 'updated_on'
    graph_y_ = ['master_overall_cycles']
    graph_shape_ = ['hv']
    graph_id_ = 'name'
    graph_legend_ = 'name'


class UpsGraph(BaseGraph):
    def __init__(self):
        BaseGraph.__init__(self)
    graph_x_ = 'updated_on'
    graph_y_ = ['input_voltage', 'load_percent', 'remaining_minutes']
    graph_shape_ = ['hv', 'hv', 'hv']
    graph_id_ = 'name'
    graph_legend_ = 'name'


class UtilityGraph(BaseGraph):
    def __init__(self):
        BaseGraph.__init__(self)
    graph_x_ = 'updated_on'
    # list fields you want saved in database
    graph_y_ = ['utility_name', 'sensor_index', 'units_delta', 'units_2_delta', 'units_total', 'ticks_delta', 'cost']
    # used for plotly
    graph_shape_ = ['hv', 'hv', 'hv', 'hv', 'hv', 'hv', 'hv']
    graph_id_ = 'sensor_name'
    graph_legend_ = 'sensor_name'
