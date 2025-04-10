import shutil
import sys
import subprocess
import os
import requests
import re
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from plyer import notification
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit, QDialog, QHBoxLayout, QProgressBar, QLabel, QFileDialog, QScrollArea, QMessageBox)
from PyQt5.QtCore import (QThread, pyqtSignal, Qt, QSize)
from PyQt5.QtGui import (QIcon, QPixmap)
from datetime import datetime

# Barra de título personalizada
class CustomTitleBar(QWidget):
    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.setFixedHeight(40)  # Altura da barra de título personalizada

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margens
        layout.setSpacing(2)

        # Configura o ícone
        self.icon_label = QLabel(self)
        pixmap = QPixmap("/usr/share/magic/assets/magic.png")  
        self.icon_label.setPixmap(pixmap.scaled(50, 50))  
        self.icon_label.setFixedWidth(50) 
        self.icon_label.setStyleSheet("margin-left: 0px; margin-right: 0px; padding: 0px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        # Título
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: white; margin: 5px; font-size: 20px;")
        self.title_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.title_label)
        
        # Botão Minimizar
        self.minimize_button = QPushButton("_")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.clicked.connect(self.minimize_window)
        self.minimize_button.setStyleSheet("background-color: #4C566A; color: white;")
        layout.addWidget(self.minimize_button)

        # Botão Fechar
        self.close_button = QPushButton("X")
        self.close_button.setFixedSize(30, 30)
        self.close_button.clicked.connect(self.close_window)
        self.close_button.setStyleSheet("background-color: #D32F2F; color: white;")
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #2E3440; color: white;")

    def minimize_window(self):
        self.parentWidget().showMinimized()

    def close_window(self):
        self.parentWidget().close()

# Pastas a serem monitoradas
MONITOR_FOLDERS = [
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Downloads/Install")
]

class DebFileHandler(FileSystemEventHandler):
    """Lida com novos arquivos .deb detectados."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_created(self, event):
        """Quando um novo arquivo é criado, verifica se é um .deb e abre automaticamente."""
        if not event.is_directory and event.src_path.endswith(".deb"):
            # print(f"📥 Novo arquivo detectado: {event.src_path}")
            self.callback(event.src_path)  # Abre automaticamente no Magic

def start_monitoring(callback):
    """Inicia o monitoramento em várias pastas."""    
    # Diretório .magic no home do usuário
    apps_dir = os.path.expanduser("~/Downloads/Install")
    os.makedirs(apps_dir, exist_ok=True)  # Cria o diretório se não existir
    
    def run():
        observers = []

        for folder in MONITOR_FOLDERS:
            if os.path.exists(folder):
                event_handler = DebFileHandler(callback)
                observer = Observer()
                observer.schedule(event_handler, folder, recursive=False)
                observer.start()
                observers.append(observer)
            else:
                print(f"⚠️ Pasta não encontrada: {folder}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            for observer in observers:
                observer.stop()

        for observer in observers:
            observer.join()

    # Inicia o monitoramento em segundo plano
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
        
class CommandExecutor(QWidget):
    # Definir sinais que serão usados para comunicação
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    command_finished_signal = pyqtSignal(str)
    finished_with_delete_signal = pyqtSignal(bool)  # Sinal para quando terminar
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.thread = None
        self.executed_command = None
        # Conecte os sinais aos slots
        self.output_signal.connect(self.update_result_area)
        self.progress_signal.connect(self.update_progress_bar)
        # Iniciar o monitoramento para abrir automaticamente ao detectar novos .deb
        start_monitoring(self.open_file_dialog)
        
    def run_commands(self):
        if not self.thread:
            self.output_signal.emit("Nenhum script de instalação padrão encontrado.")
            return
        # Acesse os métodos e sinais corretamente
        self.thread.output_signal.connect(self.update_result_area)
        self.thread.start()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove a barra de título padrão
        self.setStyleSheet("background-color: #2E3440; color: white;")
        
        # Layout principal
        layout = QVBoxLayout()

        # Adiciona a barra de título personalizada
        self.title_bar = CustomTitleBar(self, title="Magic on click")
        layout.addWidget(self.title_bar)
        
        self.setLayout(layout)
        
        # Dimensões fixas da janela
        width = 420
        height = 380
        self.setFixedSize(width, height)
        
        # Campo de texto para o comando
        self.command_input = QLineEdit(self)
        self.command_input.hide()
        self.command_input.setStyleSheet("background-color: #2E3440; color: white; margin-top: 15px; height: 30px; font-size: 20px; padding-left: 5px; border: none;")
        self.command_input.setReadOnly(False)
        layout.addWidget(self.command_input)

        # Label para exibir a detecção automática        
        self.detection_label = QLabel(self)
        self.detection_label.setAlignment(Qt.AlignCenter)
        self.detection_label.hide()
        self.detection_label.setStyleSheet("font-size: 14px; color: gray;")  # Ajuste o estilo conforme necessário
        layout.addWidget(self.detection_label)  # Adicione ao layout da interface

        # Campo para exibir o caminho do arquivo selecionado
        self.file_path_display = QLineEdit(self)
        self.file_path_display.hide()
        self.file_path_display.setStyleSheet("background-color: #2E3440; color: white; margin-top: 15px; height: 30px; font-size: 20px; padding-left: 5px; border: none;")
        self.file_path_display.setReadOnly(True)
        layout.addWidget(self.file_path_display)
        
        # Layout horizontal para os botões (lado a lado)
        horizontal_button_layout = QHBoxLayout()
        
        # Botão para limpar
        self.clear_button = QPushButton("Exit", self)
        self.clear_button.setIcon(QIcon("/usr/share/magic/assets/clear_icon.png"))
        self.clear_button.hide()
        self.clear_button.clicked.connect(self.clear_input)
        self.clear_button.setStyleSheet("background-color: #D32F2F; color: black; height: 30px; width: 100px; margin-top: 5px;")
        horizontal_button_layout.addWidget(self.clear_button)

        # Botão para executar o comando CLI
        self.execute_button = QPushButton("Execute", self)
        self.execute_button.hide()
        self.execute_button.clicked.connect(self.execute_command)
        self.execute_button.clicked.connect(self.save_commands_to_file)
        self.execute_button.setIcon(QIcon("/usr/share/magic/assets/cli_icon.png"))
        self.execute_button.setStyleSheet("background-color: #059669; color: black; height: 30px; width: 100px; margin-top: 5px;")
        horizontal_button_layout.addWidget(self.execute_button)

        # Botão para instalar pacotes
        self.install_button = QPushButton("Install", self)
        self.install_button.hide()
        self.install_button.clicked.connect(self.install_package)
        self.install_button.clicked.connect(self.save_commands_to_file)
        self.install_button.setIcon(QIcon("/usr/share/magic/assets/install_icon.png"))
        self.install_button.setStyleSheet("background-color: #059669; color: black; height: 30px; width: 100px; margin-top: 5px;")
        horizontal_button_layout.addWidget(self.install_button)

        # Adiciona o layout horizontal ao layout principal
        layout.addLayout(horizontal_button_layout)
        
        # Criar um widget para envolver o QTextEdit
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)

        # Área de texto para exibir o resultado do comando
        self.result_area = QTextEdit(self)
        self.result_area.setReadOnly(True)
        self.result_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Desativa o scroll interno
        self.result_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Desativa o scroll horizontal
        self.result_area.setStyleSheet("""
            QTextEdit {
                background-color: #2E3440; /* Define o fundo para o mesmo tom do scroll_area */
                border: none;
                color: gray;
                padding: 5px; /* Adiciona um pequeno espaço para evitar sobreposição */
                margin-top: 0px;
                margin-bottom: 0px;
            }
        """)
        result_layout.addWidget(self.result_area)

        # Criar um QScrollArea para envolver o QTextEdit
        self.result_scroll_area = QScrollArea()
        self.result_scroll_area.setWidget(result_widget)
        self.result_scroll_area.setWidgetResizable(True)
        self.result_scroll_area.hide()
        self.result_scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent; /* Deixa o fundo transparente */
                border: none; /* Remove borda padrão */
            }
            QScrollBar:vertical {
                background: #2E3440; /* Fundo do scrollbar */
                width: 8px; /* Largura da barra */
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #5C6370; /* Cor cinza da barra */
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7B8898; /* Cinza mais claro ao passar o mouse */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none; /* Remove setas de rolagem */
            }
        """)

        # Adicionar o QScrollArea ao layout principal
        layout.addWidget(self.result_scroll_area)
        self.setLayout(layout)          

        # Botões e layout
        vertical_button_layout = QHBoxLayout()
        
        self.paste_button = QPushButton("Commands", self)
        self.paste_button.setIcon(QIcon("/usr/share/magic/assets/paste_icon.png"))
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        self.paste_button.setStyleSheet("background-color: #172554; color: white; height: 35px; width: 10px; margin-top: 50px; margin-right: 0px;")
        vertical_button_layout.addWidget(self.paste_button)

        # Botão para abrir o diálogo de seleção de arquivo
        self.select_file_button = QPushButton("Packages", self)
        self.select_file_button.setIcon(QIcon("/usr/share/magic/assets/search_icon.png"))
        self.select_file_button.clicked.connect(self.open_file_dialog)
        self.select_file_button.setStyleSheet("background-color: #172554; color: white; height: 35px; width: 100px; margin-top: 50px; margin-left: 0px;")
        vertical_button_layout.addWidget(self.select_file_button)
 
        layout.addLayout(vertical_button_layout)
                
        # Variável para armazenar o caminho do arquivo
        # self.file_path = None

        self.select_file_button.setIconSize(QSize(24, 24))
        self.install_button.setIconSize(QSize(24, 24))
        self.execute_button.setIconSize(QSize(24, 24))
        self.paste_button.setIconSize(QSize(24, 24))
        self.clear_button.setIconSize(QSize(24, 24))
        
        # Função para listar os arquivos .deb
        def list_deb_files():
            downloads_path = os.path.expanduser("~/Downloads")  # Caminho para a pasta Downloads
            deb_files = [f for f in os.listdir(downloads_path) if f.endswith(".deb")]

            if deb_files:
                # Conta o total de arquivos .deb
                total_files = len(deb_files)
                
                # Numera os arquivos
                numbered_files = [f"{i + 1} - {file}" for i, file in enumerate(deb_files)]
                return total_files, "\n".join(numbered_files)  # Retorna os arquivos com numeração
            else:
                return "No '.deb' files found in ~/Downloads."

        # Obter total de arquivos e lista formatada
        total_deb_files, deb_list = list_deb_files()

        # Exibir a contagem total
        self.label_list = QLabel(f"Files available at ~/Downloads: {total_deb_files}")
        self.label_list.setStyleSheet("color: gray; margin-top: 5px; margin-bottom: 0px; margin-left: 100px;")
        layout.addWidget(self.label_list)
        
        # Criar um widget para a lista de arquivos
        file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(file_list_widget)
        
        # Exibir lista de arquivos .deb
        self.label_deb_list = QLabel(deb_list)
        self.label_deb_list.setStyleSheet("color: gray; margin-left: 0px; margin-bottom: 0px; margin-right: 5px; margin-top: 0px; padding-left: 5px;")
        self.label_deb_list.setWordWrap(True)  # Quebra de linha automática
        file_list_layout.addWidget(self.label_deb_list)

        # Criar um QScrollArea para permitir scroll quando houver muitos arquivos
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(file_list_widget)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent; /* Deixa o fundo transparente */
                border: none; /* Remove borda padrão */
            }
            QScrollBar:vertical {
                background: #2E3440; /* Fundo do scrollbar */
                width: 8px; /* Largura da barra */
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #5C6370; /* Cor cinza da barra */
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7B8898; /* Cinza mais claro ao passar o mouse */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none; /* Remove setas de rolagem */
            }
        """)

        # Adicionar ao layout principal: usar scroll apenas se houver mais de 5 arquivos
        if total_deb_files > 8:
            layout.addWidget(scroll_area, stretch=1)  # Adiciona com um peso para não expandir muito
        else:
            layout.addWidget(self.label_deb_list)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.hide()
        self.progress_bar.setFixedHeight(30)  # Define altura fixa para manter o padrão visual
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;  /* Remove qualquer borda */
                background-color: #2E3440;  /* Mesmo fundo do result_scroll_area */
                color: white; /* Cor do texto (se necessário) */
                padding: 2px;
            }
            QProgressBar::chunk {
                background-color: #059669; /* Cor do progresso */
                border-radius: 2px; /* Deixa a barra com cantos arredondados */
            }
        """)

        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
                
        # Mantém o layout horizontal
        horizontal_layout = QHBoxLayout()
        
        # Função para exibir a versão na janela
        def get_installed_version():
            try:
                path = "/usr/share/applications/magic.desktop"
                with open(path, "r") as file:
                    for line in file:
                        if line.startswith("Version"):
                            return line.split("=")[1].strip()
                return "Version not found."
            except FileNotFoundError:
                return "File not found."

        installed_version = get_installed_version()

        # Versão instalada
        sub_title_version = installed_version
        self.sub_title_version = QLabel(f"Version: {sub_title_version}")
        self.sub_title_version.setStyleSheet("color: gray; margin-left: 5px; margin-top: 5px; margin-bottom: 15px; margin-right: 200px;")
        horizontal_layout.addWidget(self.sub_title_version)
        
        # Link para o site
        self.website_link = QLabel('<a style=text-decoration:none cursor:pointer; href="https://www.magiconclick.com/programs">Magic on Click</a>')
        self.website_link.setStyleSheet("margin-right: 5px; margin-top: 5px; margin-bottom: 15px; margin-left: 5px;")
        self.website_link.setOpenExternalLinks(True)  # Habilita abertura automática no navegador
        horizontal_layout.addWidget(self.website_link)
        
        layout.addLayout(horizontal_layout)
                    
    def open_file_dialog(self, detected_file_path=None):
        """Abre o diálogo e seleciona automaticamente o arquivo detectado."""
        if detected_file_path:
            # Detectado automaticamente
            self.file_path = detected_file_path
            file_name = os.path.basename(detected_file_path)
            self.file_path_display.setText(file_name)
            self.file_path_display.show()
            self.install_button.show()
            self.paste_button.hide()
            self.select_file_button.hide()
            self.clear_button.show()
            self.label_deb_list.hide()
            self.label_list.hide()
            self.result_area.show()
            self.result_scroll_area.show()
            # Exibir a mensagem de detecção na interface ao invés de imprimir no terminal
            self.detection_label.setText(f"Package (.deb) automatically detected:\n {file_name}")
            self.detection_label.show()  # Torna a label visível
        else:
            # Abre o diálogo manualmente
            default_dir = os.path.expanduser("~/Downloads")
            options = QFileDialog.Options()
            options |= QFileDialog.ReadOnly
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Select a file", 
                default_dir, 
                "Package Debian (*.deb);;Package RPM (*.rpm);;Package Tar.gz (*.tar.gz);;", 
                options=options
            )
            
            if file_path:
                self.open_file_dialog(file_path)
                self.detection_label.hide()  # Torna a label invisível

    def install_package(self):
        if not self.file_path:
            self.result_area.setText("No files selected.")
            return
        # Detecta o tipo de arquivo selecionado
        if self.file_path.endswith(".deb"):
            self.install_deb_package()  # Chama o método para instalar .deb
        elif self.file_path.endswith(".rpm"):
            self.install_rpm_package()  # Chama o método para instalar .rpm
        elif self.file_path.endswith(".tar.gz"):
            self.install_tar_package()  # Chama o método para instalar .tar.gz
        else:
            self.result_area.setText("Unsupported file format.")
            return  

    def install_rpm_package(self):
        if not self.file_path:
            self.result_area.setText("No '.rpm' file selected.")
            return

        # Solicita a senha de administrador
        password, ok = CustomInputDialog(self).get_input()

        if not ok or not password:
            self.result_area.setText("Operation canceled or empty password.")
            return

        if self.validate_password(password):
            # Iniciar o thread para executar o comando dnf ou yum
            self.thread = CommandThread(f"echo {password} | sudo -S dnf install -y {self.file_path}", password)
            self.thread.output_signal.connect(self.update_result_area)
            self.thread.progress_signal.connect(self.update_progress_bar)
            self.thread.finished.connect(self.on_command_finished)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.thread.start()
        else:
            self.result_area.setText("Incorrect password. Please try again.")
            
    def install_deb_package(self):
        self.detection_label.hide()  # Torna a label visível
        
        if not self.file_path:
            self.result_area.setText("No '.deb' file selected.")
            return
        # Solicita a senha de administrador
        password, ok = CustomInputDialog(self).get_input()

        if not ok or not password:
            self.result_area.setText("Incorrect password. Please try again.")
            return

        if self.validate_password(password):
            # Iniciar o thread para executar o comando dpkg -i
            self.thread = CommandThread([f"echo {password} | sudo -S dpkg -i {self.file_path}"], password)
            self.thread.output_signal.connect(self.update_result_area)
            self.thread.progress_signal.connect(self.update_progress_bar)
            self.thread.command_finished_signal.connect(self.on_command_finished)
            self.thread.finished_with_delete_signal.connect(self.finished_with_delete)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.thread.start()
        else:
            self.result_area.setText("Incorrect password. Please try again.")
    
    def finished_with_delete(self):
        self.progress_bar.hide()
        self.result_area.append("\nInstallation complete.\n")

        # Extrai apenas o nome do arquivo
        file_name = os.path.basename(self.file_path)
        file_path = os.path.abspath(self.file_path)  # Obtém o caminho absoluto do arquivo

        # Exibe o diálogo para confirmar a exclusão do arquivo
        confirm_dialog = ConfirmDeleteDialog(file_path, self)
        if confirm_dialog.exec() == QDialog.Accepted:
            try:
                os.remove(file_path)
                self.result_area.setText(f"File '{file_name}' was excluded from '{file_path}' successfully.")
            except Exception as e:
                self.result_area.setText(f"Error deleting file: {e}")
        else:
            self.result_area.setText(f"File '{file_name}' will be kept in '{file_path}'.")

    def install_tar_package(self):
        if not self.file_path:
            self.result_area.setText("No '.tar.gz' file selected.")
            return

        password, ok = CustomInputDialog(self).get_input()

        if not ok or not password:
            self.result_area.setText("Operation canceled or empty password.")
            return

        if not self.validate_password(password):
            self.result_area.setText("Incorrect password. Please try again.")
            return

        self.thread = QThread()

        def run_commands():
            extract_dir = "/tmp/installed_package"
            os.makedirs(extract_dir, exist_ok=True)

            command = f"tar -xzf {self.file_path} -C {extract_dir}"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            _, stderr = process.communicate()

            if process.returncode != 0:
                self.output_signal.emit(f"Error when unzipping: '{stderr}'\n")
                shutil.rmtree(extract_dir)
                return

            self.output_signal.emit("Unzipping completed successfully.")

            install_scripts = ["install.sh", "configure.sh", "setup.sh", "execute.sh"]
            script_found = False

            for root, _, files in os.walk(extract_dir):
                for script in install_scripts:
                    if script in files:
                        script_path = os.path.join(root, script)
                        os.chmod(script_path, 0o755)

                        install_command = f"bash {script_path}"
                        process = subprocess.Popen(install_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                        _, stderr = process.communicate()

                        if process.returncode != 0:
                            self.output_signal.emit(f"Error when executing '{script}': '{stderr}'\n")
                            shutil.rmtree(extract_dir)
                            return

                        self.output_signal.emit(f"Script: '{script}', successfully executed.\n")
                        script_found = True
                        break
                if script_found:
                    break

            if not script_found:
                self.output_signal.emit(f"No installation script found.\n The file '{extract_dir}' will be removed.\n")
                shutil.rmtree(extract_dir)
                return

            move_command = f"sudo mv {extract_dir}/* /usr/local/"
            process = subprocess.Popen(move_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            _, stderr = process.communicate()

            if process.returncode != 0:
                self.output_signal.emit(f"Error moving files: '{stderr}'\n")
            else:
                self.output_signal.emit("Files moved successfully.")

            shutil.rmtree(extract_dir)
            self.output_signal.emit(f"\nDirectory: '{extract_dir}', successfully removed.\n")

        # Crie uma instância do `InstallThread` passando a função `run_commands`
        self.thread.run = run_commands        
        self.thread.start()

    def on_command_finished(self):
        self.progress_bar.setValue(100)
        # Extrai apenas o nome do arquivo sem o caminho completo
        file_name = os.path.basename(self.file_path)
        self.result_area.append(f"\nPackage: '{file_name}', installed successfully.\n")

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        current_text = clipboard.text().strip()
        if current_text:
            self.last_clipboard_text = current_text
            self.command_input.setText(current_text)
            self.command_input.show()
            self.execute_button.show()
            self.paste_button.hide()
            self.select_file_button.hide()
            self.result_area.show()
            self.label_deb_list.hide()
            self.label_list.hide()
            self.clear_button.show()
            self.result_scroll_area.show()
            self.detection_label.hide()
            
    def clear_input(self):
        self.progress_bar.setValue(0)
        self.result_area.clear()
        self.progress_bar.hide()
        self.execute_button.hide()
        self.install_button.hide()
        self.command_input.hide()
        self.file_path_display.hide()
        self.paste_button.show()
        self.select_file_button.show()
        self.clear_button.hide()
        self.label_deb_list.show()
        self.label_list.show()        
        self.result_area.hide()
        self.result_scroll_area.hide()
        self.detection_label.hide()

    def execute_command(self):
        self.result_area.clear()
                
        command = self.command_input.text().strip()
        if not command:
            self.result_area.setText("Empty command. Copy the command to be executed.")
            return
        # Dividir o comando usando barra como separador
        commands = command.split("\\")  # Divide os comandos separados por "\\"
        # Remover comandos vazios que podem ter vindo após a separação
        commands = [cmd.strip() for cmd in commands if cmd.strip()]
        
        # Palavras-chave a serem verificadas
        keywords = ["remove", "purge", "uninstall", "delete", "upgrade", "install", "autoremove", "autoclean"]
        keyword_update = "update"  # Palavra-chave que exige 'sudo'
        # keyword_update_variants = ["sudo apt update", "sudo apt-get update"]  # Ambos os comandos suportados
             
        # Iterar sobre cada comando e verificar se ele contém palavras exatas das keywords
        for cmd in commands:
            # Dividir o comando em palavras individuais
            words = cmd.split()
            
            # Verificar se o comando contém a palavra "update"
            if keyword_update in words:
                if "sudo" not in cmd:
                    self.result_area.setText(
                        f"The command '{cmd}' contains '{keyword_update}' and needs to include 'sudo' to run."
                    )
                    return  # Para aqui, pois encontrou um problema
            
            # Verificar outras palavras-chave
            for keyword in keywords:
                if keyword in words:
                    if "sudo" not in cmd:
                        self.result_area.setText(
                            f"The command '{cmd}' contains '{keyword_update}' and needs to include 'sudo' to run."
                        )
                        return  # Interrompe aqui, pois há um problema com o comando
            
            # Verificar se alguma palavra do comando está na lista de keywords
            if any(word in keywords for word in words):
                # Verificar se o comando já contém -y ou --yes
                if "-y" not in cmd and "--yes" not in cmd:
                    # Exibir mensagem pedindo correção para aquele comando específico
                    self.result_area.setText(
                        f"The command '{cmd}' needs '-y' or '--yes' for automatic execution."
                    )
                    return  # Para aqui, pois encontrou um comando que precisa de correção
                
        if not commands:
            self.result_area.setText("No valid commands provided.")
            return
        
        # Se um dos comandos "sudo apt update" ou "sudo apt-get update" for detectado, adiciona "apt list --upgradable"
        # if any(update_cmd in commands for update_cmd in keyword_update_variants):
        #     commands.append("apt list --upgradable")        

        if "sudo" in command:
            password, ok = CustomInputDialog(self).get_input()
            if ok:
                if not password:
                    self.result_area.setText("Empty password field. Please try again.")
                    return
                # Validar a senha
                if self.validate_password(password):
                    # Iniciar o thread para executar todos os comandos com sudo
                    sudo_commands = [f"echo {password} | sudo -S {cmd}" for cmd in commands]
                    self.thread = CommandThread(sudo_commands, password)
                else:
                    self.result_area.setText("Incorrect password. Please try again.")
                    return
            else:
                self.result_area.setText("Operation canceled by user.")
                return
        else:
            # Executar os comandos sem sudo
            self.thread = CommandThread(commands)

        # Conectar sinais
        self.thread.output_signal.connect(self.update_result_area)
        self.thread.progress_signal.connect(self.update_progress_bar)
        self.thread.command_finished_signal.connect(self.print_command_completion)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.thread.start()

    def validate_password(self, password):
        try:
            # O uso de -S já está correto aqui para ler a senha via stdin
            subprocess.check_output(f"sudo -k && echo {password} | sudo -S -v", shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            return True
        except subprocess.CalledProcessError as e:
            self.result_area.setText(f"Validation error: '{e.output}'\n")  # Mostrar o erro no resultado
            return False

    def save_commands_to_file(self):
        # Pega a data e hora atual no formato desejado
        timestamp_date = datetime.now().strftime("%Y-%m-%d")
        timestamp_hour = datetime.now().strftime("%H:%M:%S")
        
        # Diretório .magic no home do usuário
        magic_dir = os.path.expanduser("~/.magic")
        os.makedirs(magic_dir, exist_ok=True)  # Cria o diretório se não existir
        
        # Caminho completo para o arquivo de saída
        output_file = os.path.join(magic_dir, "commands_history.txt")

        # Coleta as entradas
        try:
            file_path = self.file_path_display.text().strip()
            command_text = self.command_input.text().strip()

            # Verifica se há algo para salvar
            if not command_text and not file_path:
                self.result_area.append("No commands or files selected.")
                return

            # Contar quantos comandos já existem no arquivo
            command_count = 1  # Começa do 1 se o arquivo não existir
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    lines = f.readlines()
                    command_count = sum(1 for line in lines if line.startswith("#")) + 1

            # Escreve as entradas no arquivo com numeração
            with open(output_file, "a") as f:
                if command_text:
                    f.write(f"#{command_count}:\n")
                    f.write(f"Date: {timestamp_date}\nTime: {timestamp_hour}\nCommand: {command_text}\n")
                if file_path:
                    f.write(f"#{command_count}:\n")
                    f.write(f"Date: {timestamp_date}\nTime: {timestamp_hour}\nPackage: {file_path}\n")
                f.write("-" * 30 + "\n")  # Separador para facilitar leitura

            # Mensagem de confirmação
            self.result_area.append(f"#{command_count} saved in {magic_dir} successfully.")

        except Exception as e:
            self.result_area.append(f"Error saving entries: '{str(e)}'\n")

    def update_result_area(self, output):
        self.result_area.append(output)

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)

    def print_command_completion(self, commands):
        self.progress_bar.setValue(100)
        # Usando expressão regular para remover tudo até e incluindo '-S'
        result_command = re.sub(r".*-S\s*", "", commands).strip()
        # Imprime o comando atual finalizado
        self.result_area.append(f"\nCommand: '{result_command}', executed successfully.\n")

    def closeEvent(self, event):
        install_folder = os.path.expanduser("~/Downloads/Install")
        # Verifica se a pasta existe antes de tentar excluir
        if os.path.exists(install_folder):
            try:
                shutil.rmtree(install_folder)  # Remove a pasta e todo o conteúdo
                print(f"Pasta '{install_folder}' excluída ao fechar o Magic.")
            except Exception as e:
                print(f"Erro ao excluir '{install_folder}': {e}")
        event.accept()  # Fecha o aplicativo normalmente

class ConfirmDeleteDialog(QDialog):
    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.file_name = file_name
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove a barra de título padrão
        self.setStyleSheet("""
            QDialog {
                background-color: #2E3440;
                border: 1px solid #111827;
                color: white;
            }
            QPushButton {
                background-color: #81A1C1;
                color: white;
                padding: 5px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #88C0D0;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
        """)

        layout = QVBoxLayout()
        
        # Barra de título personalizada
        self.title_bar = CustomTitleBar(self, title="Choose an option")
        layout.addWidget(self.title_bar)

        # Definir o tamanho do diálogo
        self.setLayout(layout)
        self.setGeometry(50, 50, 320, 220)

        # Mensagem de confirmação
        file_label = QLabel(f"{self.file_name}")
        file_label.setAlignment(Qt.AlignCenter)
        file_label.setStyleSheet("margin-top: 5px;")
        file_label.setWordWrap(True)
        layout.addWidget(file_label)

        # Layout para os botões
        button_layout = QHBoxLayout()

        # Botão Excluir
        self.delete_button = QPushButton("Remove")
        self.delete_button.clicked.connect(self.accept)
        self.delete_button.setStyleSheet("background-color: #D32F2F; color: white; margin-bottom: 25px;")
        button_layout.addWidget(self.delete_button)

        # Botão Manter
        self.cancel_button = QPushButton("Keep")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("background-color: #059669; color: white; margin-bottom: 25px;")
        button_layout.addWidget(self.cancel_button)

        # Adicionar o layout de botões ao layout principal
        layout.addLayout(button_layout)        

# Classe para criar o diálogo de senha personalizado com barra de título personalizada
class CustomInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove a barra de título padrão
        self.setStyleSheet("""
            QDialog {
                background-color: #2E3440;
                border: 1px solid #111827;
                color: white;
            }
            QLineEdit {
                background-color: #2E3440;
                color: white;
                border: 1px solid #111827;
                border-radius: 2px;
                padding: 5px;
            }
            QPushButton {
                background-color: #81A1C1;
                color: white;
                padding: 5px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #88C0D0;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
        """)

        layout = QVBoxLayout()

        # Barra de título personalizada
        self.title_bar = CustomTitleBar(self, title="Your password")
        layout.addWidget(self.title_bar)

        self.setLayout(layout)
        self.setGeometry(50, 50, 320, 220)

        # Campo de entrada de senha
        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText("*******")
        self.line_edit.setEchoMode(QLineEdit.Password)  # Define modo de senha (oculta o texto)
        self.line_edit.setFocus(True)
        layout.addWidget(self.line_edit)

        # Layout para os botões
        button_layout = QHBoxLayout()

        # Botão Cancelar
        self.cancel_button = QPushButton("Exit")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("background-color: #D32F2F; color: white;")
        button_layout.addWidget(self.cancel_button)
 
        # Botão OK
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setStyleSheet("background-color: #059669; color: white;")
        button_layout.addWidget(self.ok_button)

        # Conectar o evento Enter ao botão OK
        self.line_edit.returnPressed.connect(self.ok_button.click)

        # Adicionar os botões ao layout principal
        layout.addLayout(button_layout)
        # self.setLayout(layout)

    def get_input(self):
        if self.exec_() == QDialog.Accepted:
            return self.line_edit.text(), True
        else:
            return "", False

class CommandThread(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    input_required_signal = pyqtSignal(str)
    command_finished_signal = pyqtSignal(str)
    finished_with_delete_signal = pyqtSignal(bool)
    def __init__(self, commands, password=None):
        super().__init__()
        self.commands = commands
        self.process = None
        self.password = password  # Armazena a senha, se houver
        self.total_lines = 1  # Conta o total de linhas de saída lidas

    def run(self):
        total_commands = len(self.commands)
        progress = 0
        step = 100 // total_commands if total_commands > 0 else 100

        for command in self.commands:
            try:
                if "sudo" in command and self.password:
                    # Executa o comando com a senha enviada para o stdin
                    self.process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                    self.process.stdin.write(self.password + "\n")
                    self.process.stdin.flush()
                else:
                    # Executa comandos sem sudo
                    self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                while True:                    
                    try:
                        output = self.process.stdout.readline().strip()

                        if output == "" and self.process.poll() is not None:
                            break
                        if output:
                            self.output_signal.emit(output.strip())                        
                            # Incrementa progressivamente conforme a saída vai sendo lida
                            self.total_lines += 1
                            progress = min(100, (self.total_lines * 1)) 
                            self.progress_signal.emit(progress)
                            
                        if self.process.poll() is not None:
                            break
                    except:
                        pass
                progress = (self.commands.index(command) + 1) * step
                self.progress_signal.emit(progress)

                self.command_finished_signal.emit(command)
            
            except Exception as e:
                self.output_signal.emit(f"Error executing command: '{str(e)}'\n")

        self.progress_signal.emit(100)
        self.finished_with_delete_signal.emit(True)

    def terminate_process(self):
        if self.process:
            self.process.terminate()
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    executor = CommandExecutor()
    executor.show()
    sys.exit(app.exec())
