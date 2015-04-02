
kill $(ps aux | grep '[p]ython run_all.py' | awk '{print $2}')
