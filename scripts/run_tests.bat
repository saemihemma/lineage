@echo off
REM Simple test runner for Windows
REM Runs all unit tests and exits with appropriate exit code

cd /d "%~dp0\.."

REM Run tests using Python's unittest discover
python -m unittest discover -v

REM Exit with the test result code
exit /b %ERRORLEVEL%

