import socket
import os
import sys

# Configurações
HOST = '127.0.0.1' 
PORT = 65432
BUFFER_SIZE = 4096 
DOWNLOAD_DIR = 'client_downloads'

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- Funções do Cliente ---

def connect_to_server():
    """Cria e retorna o socket conectado."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
        return s
    except ConnectionRefusedError:
        print("Erro: Servidor indisponível.")
        sys.exit()

def send_and_receive(sock, command):
    """Envia um comando simples e espera a resposta inicial do servidor."""
    sock.sendall(command.encode('utf-8'))
    response = sock.recv(1024).decode('utf-8').strip()
    return response

def handle_upload(sock, filename):
    """Lida com a lógica de Upload de um arquivo."""
    if not os.path.exists(filename):
        print(f"Erro: Arquivo local '{filename}' não encontrado.")
        return

    file_size = os.path.getsize(filename)
    
    # 1. Envia comando UPLOAD com metadados
    command = f"UPLOAD {os.path.basename(filename)} {file_size}"
    sock.sendall(command.encode('utf-8'))
    
    # 2. Espera a confirmação do servidor
    response = sock.recv(1024).decode('utf-8').strip()
    if not response.startswith("READY_TO_RECEIVE"):
        print(f"Erro no servidor: {response}")
        return

    # 3. Envia os bytes do arquivo
    print(f"Iniciando upload de {filename} ({file_size} bytes)...")
    with open(filename, 'rb') as f:
        while True:
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
                break
            sock.sendall(bytes_read)

    # 4. Recebe a confirmação final
    final_response = sock.recv(1024).decode('utf-8').strip()
    print(f"Servidor: {final_response}")

def handle_download(sock, filename):
    """Lida com a lógica de Download de um arquivo."""
    
    # 1. Envia o comando DOWNLOAD
    command = f"DOWNLOAD {filename}"
    sock.sendall(command.encode('utf-8'))

    # 2. Recebe metadados (tamanho e status) do servidor
    response = sock.recv(1024).decode('utf-8').strip()
    
    if response.startswith("ERROR"):
        print(f"Erro: {response}")
        return

    if response.startswith("READY_TO_SEND"):
        try:
            _, received_filename, file_size_str = response.split()
            file_size = int(file_size_str)
        except ValueError:
            print("Erro: Metadados de download inválidos.")
            return

        # 3. Confirma que está pronto para receber
        sock.sendall("ACK_READY".encode('utf-8'))
        
        # 4. Recebe e salva os bytes do arquivo
        filepath = os.path.join(DOWNLOAD_DIR, received_filename)
        print(f"Iniciando download de {received_filename} ({file_size} bytes) para {filepath}...")
        
        bytes_received = 0
        with open(filepath, 'wb') as f:
            while bytes_received < file_size:
                # O chunk máximo é o mínimo entre o buffer e o que falta receber
                chunk = sock.recv(min(file_size - bytes_received, BUFFER_SIZE)) 
                if not chunk:
                    break
                f.write(chunk)
                bytes_received += len(chunk)
        
        if bytes_received == file_size:
            print(f"SUCESSO: {received_filename} baixado completamente.")
        else:
            print(f"AVISO: Download de {received_filename} incompleto. {bytes_received}/{file_size}")

def main_client():
    """Loop principal do cliente (interface de linha de comando)."""
    sock = connect_to_server()
    print("Conectado ao servidor de arquivos. Use 'HELP' para comandos.")
    
    while True:
        command_line = input("Cliente> ").strip()
        parts = command_line.split()
        
        if not parts:
            continue
        
        command = parts[0].upper()

        if command == "LOGIN":
            if len(parts) == 3:
                response = send_and_receive(sock, command_line)
                print(f"Servidor: {response}")
            else:
                print("Uso: LOGIN <username> <password>")

        elif command == "UPLOAD":
            if len(parts) == 2:
                handle_upload(sock, parts[1])
            else:
                print("Uso: UPLOAD <caminho_do_arquivo_local>")

        elif command == "DOWNLOAD":
            if len(parts) == 2:
                handle_download(sock, parts[1])
            else:
                print("Uso: DOWNLOAD <nome_do_arquivo_no_servidor>")

        elif command == "LOGOUT":
            response = send_and_receive(sock, command_line)
            print(f"Servidor: {response}")
            break

        elif command == "EXIT" or command == "QUIT":
            # Envia LOGOUT se a conexão ainda estiver ativa
            sock.sendall("LOGOUT".encode('utf-8')) 
            break

        elif command == "HELP":
            print("\n--- Comandos Disponíveis ---")
            print("LOGIN <user> <pass>  - Autentica no sistema.")
            print("UPLOAD <local_path>  - Envia um arquivo local para o servidor.")
            print("DOWNLOAD <file_name> - Baixa um arquivo do servidor.")
            print("LOGOUT               - Desloga do sistema e encerra.")
            print("EXIT                 - Encerra o cliente.")
            print("--------------------------\n")

        else:
            print(f"Comando '{command}' não reconhecido.")

    sock.close()
    print("Conexão encerrada.")

if __name__ == "__main__":
    main_client()