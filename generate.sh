#!/bin/bash
set -e  # Para o script em caso de erro

# Variáveis
APP_NAME="magic-on-click"
SOURCE_FILE="src/main.py"
DIST_DIR="dist"
PACKAGE_DIR="./magic-on-click"
BIN_PATH="$PACKAGE_DIR/usr/bin"
PYINSTALLER_OPTIONS="--onefile"
DEBIAN_DIR="./DEBIAN"

echo "1. Gerando o binário com PyInstaller..."
pyinstaller $PYINSTALLER_OPTIONS --name $APP_NAME --distpath $DIST_DIR $SOURCE_FILE

# Verificar se o binário foi gerado com sucesso
if [ ! -f "$DIST_DIR/$APP_NAME" ]; then
    echo "Erro: Binário não encontrado em $DIST_DIR!"
    exit 1
fi

echo "2. Copiando arquivos para o diretório do pacote..."
mkdir -p $BIN_PATH  # Garante que o diretório binário existe
cp -R ./usr/ $PACKAGE_DIR
cp -R $DEBIAN_DIR $PACKAGE_DIR/  # Copia o diretório DEBIAN/
cp -R "$DIST_DIR/$APP_NAME" "$BIN_PATH/magic"

echo "3. Configurando permissões..."
sudo chmod +x "$BIN_PATH/magic"
sudo chmod +x /usr/share/magic/assets/hicolor/256x256/apps/magic.png

echo "Binario gerado com sucesso!"
