__author__ = 'dcristian'
import utils
from main import logger

query_count = None
query_cumulative_time_miliseconds = None
min_query_time_miliseconds = None
max_query_time_miliseconds = None


def add_query(start_time, query_details=None):
        elapsed = int((utils.get_base_location_now_date() - start_time).total_seconds()*1000)
        global query_count, query_cumulative_time_miliseconds
        global min_query_time_miliseconds, max_query_time_miliseconds

        if not query_count:
            query_count = 0
            query_cumulative_time_miliseconds = 0
            max_query_time_miliseconds = elapsed
            min_query_time_miliseconds = elapsed

        if max_query_time_miliseconds < elapsed:
            max_query_time_miliseconds = elapsed
            logger.info("Longest query details:{}".format(query_details))

        if min_query_time_miliseconds > elapsed:
            min_query_time_miliseconds = elapsed

        query_count += 1
        query_cumulative_time_miliseconds += elapsed
        logger.debug("Count={} avg={} min={} max={}".format(query_count,
                        query_cumulative_time_miliseconds/query_count,
                        min_query_time_miliseconds, max_query_time_miliseconds))
        return elapsed
