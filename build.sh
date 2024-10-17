#!/bin/bash

VERSION=$1  # Recebe a versão como argumento (ex: 1.0.1)
PACKAGE_NAME="magic-on-click"

if [ -z "$VERSION" ]; then
  echo "Erro: A versão não foi fornecida."
  echo "Uso: ./build.sh <versão>"
  exit 1
fi

echo "Atualizando versão para $VERSION..."

# Atualiza a versão no arquivo control
sed -i "s/^Version:.*/Version: $VERSION/" $PACKAGE_NAME/DEBIAN/control

# Atualiza a versão no arquivo .desktop (caso tenha essa linha)
sed -i "s/^Version=.*/Version=$VERSION/" $PACKAGE_NAME/usr/share/applications/magic.desktop

# Atualiza a versão no arquivo version
sed -i "s/^v.*/v$VERSION/" $PACKAGE_NAME/usr/lib/magic/version

# Garante que o arquivo .desktop está acessível
if [ ! -f $PACKAGE_NAME/usr/share/applications/magic.desktop ]; then
  echo "Erro: O arquivo magic.desktop não foi encontrado."
  exit 1
fi

# Cria o pacote .deb
dpkg-deb --build --root-owner-group $PACKAGE_NAME

# Renomeia o pacote para incluir a versão
mv ${PACKAGE_NAME}.deb ${PACKAGE_NAME}_${VERSION}.deb

echo "Pacote ${PACKAGE_NAME}_${VERSION}.deb criado com sucesso!"
