SET "ANACONDAP=%HOMEDRIVE%\tools\miniconda3"
SET "CURDIR=%~dp0"

cd /d "%CURDIR%"

%windir%\System32\cmd.exe "/K" "%ANACONDAP%\Scripts\activate.bat %ANACONDAP% & cd %ANACONDAP%\envs & conda activate gpu & cd %CURDIR% & python Launcher.py