@echo off
SET STATUS=,
:START:
python.exe mcedit.py
ECHO.
ECHO ^|-----------------^|
ECHO ^|Mcedit Terminated^|
ECHO ^|-----------------^|
ECHO.
SET /P K=Press Y to restart MCEdit%STATUS% any other key to exit:
IF /I %K%==Y GOTO CLEAR

GOTO EXIT

:CLEAR:
CLS
SET STATUS= again,
GOTO START

:EXIT: