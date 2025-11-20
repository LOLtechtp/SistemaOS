#!/bin/bash

echo ""
echo "====================================="
echo "      GESTOR OS - DEPLOY CHECK"
echo "====================================="
echo ""

# Caminho do projeto no PA (igual ao GitHub)
cd ~/SistemaOS

# Teste se estamos no diretório correto
if [ ! -d ".git" ]; then
    echo "❌ ERRO: Este diretório não é um repositório Git."
    exit 1
fi

# Verifica modificações locais
CHANGES=$(git status --porcelain)

echo ""
date +"📅 Data: %d/%m/%Y  ⏰ Hora: %H:%M:%S"
echo ""

if [ -z "$CHANGES" ]; then
    echo "✔ Nenhuma modificação local detectada."
    echo "🔄 Executando git pull..."
    git pull
    echo "✔ Deploy concluído sem conflitos."
    exit 0
else
    echo "⚠ Alterações locais detectadas:"
    echo ""
    git status
    echo ""
    echo "O que deseja fazer?"
    echo ""
    echo "  [A] Limpar tudo e sincronizar com GitHub"
    echo "  [B] Guardar alterações (stash)"
    echo "  [C] Cancelar"
    echo ""
    read -p "Escolha A, B ou C: " OP

    case $OP in
        A|a)
            echo "🔨 Limpando local..."
            git restore .
            git clean -f
            echo "🔄 Sincronizando..."
            git pull
            echo "✔ Ambiente alinhado com GitHub."
            ;;

        B|b)
            echo "📦 Salvando alterações locais (stash)..."
            git stash
            echo "🔄 Sincronizando com GitHub..."
            git pull
            echo "✔ Mudanças guardadas! (git stash list)"
            ;;

        C|c)
            echo "❌ Cancelado."
            exit 0
            ;;

        *)
            echo "❌ Opção inválida."
            exit 1
            ;;
    esac
fi

echo "====================================="
echo " DEPLOY FINALIZADO "
echo "====================================="
