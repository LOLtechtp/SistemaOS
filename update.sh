#!/bin/bash
cd /home/Loltechtp/SistemaOS
source venv/bin/activate
git pull
flask db upgrade
touch /var/www/Loltechtp_pythonanywhere_com_wsgi.py
echo "✅ Projeto atualizado e migrações aplicadas com sucesso!"
