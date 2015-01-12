@echo off
SET STATUS=,
:START:
python.exe mcedit.py
ECHO.
ECHO ^|-----------------^|
ECHO ^|Mcedit Terminated^|
ECHO ^|-----------------^|
ECHO.
SET K==R
SET /P K=Press R or Enter to restart MCEdit%STATUS% any other key to exit:
IF /I %K%==R GOTO CLEAR

GOTO EXIT

:CLEAR:
CLS
SET STATUS= again,
GOTO START

:EXIT: