@echo off
cd /d C:\Bussula Publica\scripts
call .venv\Scripts\activate
python extract.py
python transform_load.py
python gerar_embeddings.py
python classificar_temas.py
echo Pipeline semanal finalizado em %date% %time% >> logs\pipeline.log
