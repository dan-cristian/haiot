from main.logger_helper import L
from main.admin import models


# energy rule
def rule_energy_plug_1(obj=models.Utility(), field_changed_list=None):
    #Log.logger.info("changed list is {}".format(field_changed_list))
    if field_changed_list is not None:
        if 'utility_name' in field_changed_list:
            if obj.utility_name == 'power main mono':
                if obj.units_2_delta < 0:
                    L.l.info("Exporting power {}w".format(obj.units_2_delta))
                else:
                    L.l.info("Importing power {}w".format(obj.units_2_delta))
