__author__ = 'dcristian'
from main import db

class BaseGraph:
    save_to_graph = False
    @property
    def graph_x_(self): raise NotImplementedError
    @property
    def graph_y_(self): raise NotImplementedError
    @property
    def graph_id_(self): raise NotImplementedError
    @property
    def graph_legend_(self): raise NotImplementedError
    def comparator_unique_graph_record(self): raise NotImplementedError

class SensorGraph(BaseGraph):
    graph_x_ = 'updated_on'
    graph_y_ = ['temperature', 'humidity']
    graph_shape_ = ['spline','spline']
    graph_id_ = 'address'
    graph_legend_ = 'sensor_name'

class SystemMonitorGraph(BaseGraph):
    graph_x_ = 'updated_on'
    graph_y_ = ['cpu_usage_percent', 'memory_available_percent', 'uptime_days']
    graph_shape_ = ['spline','spline','hv']
    graph_id_ = 'name'
    graph_legend_ = 'name'

class SystemDiskGraph(BaseGraph):
    graph_x_ = 'updated_on'
    graph_y_ = ['temperature', 'power_status', 'sector_error_count', 'load_cycle_count', 'start_stop_count']
    graph_shape_ = ['spline','hv','hv','hv','hv']
    graph_id_ = 'serial'
    graph_legend_ = 'hdd_name'
