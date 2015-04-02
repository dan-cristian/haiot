
#echo Enter mem[Enter] to run db in memory. Default is from disk
#read -t 3 answer
#if [ $? == 0 ]; then
#    echo "Selected"
#else
#    echo "Can't wait anymore!"
#answer=disk
#fi
#echo "Your answer is: $answer"
scripts/stopserver.sh
source venv/bin/activate
python run_all.py disk