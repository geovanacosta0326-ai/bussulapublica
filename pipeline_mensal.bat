@echo off
cd /d C:\Bussula Publica\scripts
call .venv\Scripts\activate
python extract_despesa.py
python transform_load_despesa.py
echo Pipeline mensal finalizado em %date% %time% >> logs\pipeline.log
