Name: magic-on-click
Version: 1.1
Release: 1%{?dist}
Summary: Magic On Click
License: GPL
Source0: %{name}-%{version}.tar.gz
BuildArch: x86_64

%description
Uma ferramenta gráfica de instalação para software no Linux.

%install
install -D -m0755 %{buildroot}/dist/magic-on-click %{buildroot}/usr/bin/magic

%files
/usr/bin/magic
/usr/share/applications/magic.desktop
/usr/share/magic/assets/hicolor/48x48/apps/magic.png
