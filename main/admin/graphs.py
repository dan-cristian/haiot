__author__ = 'dcristian'


class BaseGraph:
    def __init__(self):
        pass

    save_to_graph = False  # if true this record will be uploaded to a graph
    last_save_to_graph = None  # last date, used to upload with a certain frequency
    save_to_history = False  # if true this record will be saved to master node database for reporting

    @property
    def graph_x_(self): raise NotImplementedError

    @property
    def graph_y_(self): raise NotImplementedError

    @property
    def graph_id_(self): raise NotImplementedError

    @property
    def graph_legend_(self): raise NotImplementedError


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
    graph_y_ = ['units_delta', 'units_total', 'ticks_delta']
    graph_shape_ = ['hv', 'hv', 'hv']
    graph_id_ = 'sensor_name'
    graph_legend_ = 'sensor_name'


class PresenceGraph(BaseGraph):
    def __init__(self):
        BaseGraph.__init__(self)
