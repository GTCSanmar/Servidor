import socket
import threading
import os
import hashlib

# Configurações do Servidor
HOST = '127.0.0.1' # Loopback
PORT = 65432
FILE_STORAGE = 'server_files'

# Banco de Dados de Usuários (simulação)
USERS = {
    "alice": "senha123",
    "bob": "securepass"
}

if not os.path.exists(FILE_STORAGE):
    os.makedirs(FILE_STORAGE)

# --- Funções de Ajuda ---

def authenticate_user(username, password):
    """Verifica credenciais."""
    return USERS.get(username) == password

def handle_client(conn, addr):
    """Lida com as requisições de um cliente específico em uma thread."""
    print(f"[*] Nova conexão de {addr}")
    logged_in_user = None

    try:
        while True:
            # Recebe o comando do cliente (tamanho fixo para o comando)
            # Decodifica para string e remove espaços em branco
            data = conn.recv(1024).decode('utf-8').strip() 
            if not data:
                break # Conexão fechada

            parts = data.split()
            command = parts[0].upper()

            # --- Tratamento de Comandos ---

            if command == "LOGIN":
                if len(parts) == 3:
                    username, password = parts[1], parts[2]
                    if authenticate_user(username, password):
                        logged_in_user = username
                        # Cria o diretório do usuário se não existir
                        if not os.path.exists(os.path.join(FILE_STORAGE, username)):
                            os.makedirs(os.path.join(FILE_STORAGE, username))
                        conn.sendall("SUCCESS Login bem-sucedido.".encode('utf-8'))
                        print(f"[*] {username} logado.")
                    else:
                        conn.sendall("ERROR Credenciais inválidas.".encode('utf-8'))
                else:
                    conn.sendall("ERROR Formato de LOGIN inválido.".encode('utf-8'))

            elif not logged_in_user:
                # Bloqueia comandos que exigem login
                conn.sendall("ERROR Faça login primeiro.".encode('utf-8'))
            
            elif command == "LOGOUT":
                logged_in_user = None
                conn.sendall("SUCCESS Desconectado.".encode('utf-8'))
                print(f"[*] {addr} deslogou.")
                break

            elif command == "UPLOAD":
                if len(parts) == 3:
                    filename = parts[1]
                    try:
                        file_size = int(parts[2])
                    except ValueError:
                        conn.sendall("ERROR Tamanho do arquivo inválido.".encode('utf-8'))
                        continue
                    
                    conn.sendall("READY_TO_RECEIVE".encode('utf-8'))
                    
                    filepath = os.path.join(FILE_STORAGE, logged_in_user, filename)
                    bytes_received = 0
                    
                    # Recebe os bytes do arquivo
                    with open(filepath, 'wb') as f:
                        while bytes_received < file_size:
                            chunk = conn.recv(min(file_size - bytes_received, 4096))
                            if not chunk:
                                break
                            f.write(chunk)
                            bytes_received += len(chunk)

                    if bytes_received == file_size:
                        conn.sendall(f"SUCCESS {filename} enviado com sucesso.".encode('utf-8'))
                        print(f"[*] {logged_in_user} UPLOAD de {filename} concluído.")
                    else:
                        os.remove(filepath) # Remove o arquivo incompleto
                        conn.sendall("ERROR Transferência interrompida.".encode('utf-8'))
                else:
                    conn.sendall("ERROR Formato de UPLOAD inválido.".encode('utf-8'))

            elif command == "DOWNLOAD":
                if len(parts) == 2:
                    filename = parts[1]
                    filepath = os.path.join(FILE_STORAGE, logged_in_user, filename)
                    
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        # 1. Envia metadados (pronto para enviar + nome + tamanho)
                        conn.sendall(f"READY_TO_SEND {filename} {file_size}".encode('utf-8'))
                        
                        # Espera um ACK (Confirmação) do cliente antes de enviar os dados
                        # para evitar que os dados do arquivo se misturem com a resposta
                        ack = conn.recv(1024).decode('utf-8').strip()
                        if ack != "ACK_READY":
                            print(f"ERRO: Cliente não confirmou prontidão.")
                            continue

                        # 2. Envia os bytes do arquivo
                        with open(filepath, 'rb') as f:
                            while True:
                                bytes_read = f.read(4096)
                                if not bytes_read:
                                    break
                                conn.sendall(bytes_read)
                        
                        print(f"[*] {logged_in_user} DOWNLOAD de {filename} concluído.")
                    else:
                        conn.sendall("ERROR Arquivo não encontrado.".encode('utf-8'))
                else:
                    conn.sendall("ERROR Formato de DOWNLOAD inválido.".encode('utf-8'))

            else:
                conn.sendall("ERROR Comando desconhecido.".encode('utf-8'))

    except Exception as e:
        print(f"[!] Erro na comunicação com {addr}: {e}")
    finally:
        print(f"[*] Conexão com {addr} encerrada.")
        conn.close()

# --- Loop Principal do Servidor ---

def start_server():
    """Inicia o servidor e escuta por conexões."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[*] Servidor escutando em {HOST}:{PORT}")

        while True:
            # Aceita uma nova conexão
            conn, addr = server_socket.accept()
            # Inicia uma nova thread para lidar com o cliente
            client_thread = threading.Thread(target=handle_client, args=(conn, addr,))
            client_thread.start()

    except Exception as e:
        print(f"[CRITICAL] Erro ao iniciar o servidor: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()