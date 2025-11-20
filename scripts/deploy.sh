#!/bin/bash

echo ""
echo "====================================="
echo "      GESTOR OS - DEPLOY CHECK"
echo "====================================="
echo ""

cd ~/SistemaOS || exit 1

if [ ! -d ".git" ]; then
    echo "❌ ERRO: não é um repo Git."
    exit 1
fi

echo ""
date +"📅 %d/%m/%Y  ⏰ %H:%M:%S"
echo ""

CHANGES=$(git status --porcelain)

echo "▶ Rodando testes ANTES de sincronizar..."
pytest -q
if [ $? -ne 0 ]; then
    echo "❌ Testes falharam — deploy bloqueado."
    exit 1
fi
echo "✔ Testes ok!"

if [ -z "$CHANGES" ]; then
    echo "✔ Sem alterações locais — puxando do GitHub..."
    git pull
    exit 0
fi

echo "⚠ Alterações locais encontradas:"
git status

echo "Escolha:"
echo "  [A] Limpar tudo (restore + clean + pull)"
echo "  [B] Stash"
echo "  [C] Cancelar"

read -p "Opção:" OP

case $OP in
    A|a)
        git restore .
        git clean -f
        git pull
        ;;
    B|b)
        git stash
        git pull
        ;;
    C|c)
        exit 0
        ;;
    *)
        exit 1
        ;;
esac

echo "====================================="
echo " DEPLOY FINALIZADO "
echo "====================================="
