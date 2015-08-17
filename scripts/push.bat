call makelinks-github.bat
rem cd ..
git add -A
git commit  -m "%COMPUTERNAME% %USERNAME%" -a
git push