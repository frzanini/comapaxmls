import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import time

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ArquivoInfo:
    """Representa informações de um arquivo."""
    nome: str
    caminho_completo: str
    extensao: str
    tamanho: int

class GerenciadorArquivos:
    """Classe para gerenciamento e análise de arquivos em diretórios."""
    
    @staticmethod
    def obter_info_arquivo(caminho: Path) -> Optional[ArquivoInfo]:
        """
        Obtém informações de um arquivo específico.
        
        Args:
            caminho: Path do arquivo a ser analisado
        
        Returns:
            ArquivoInfo se sucesso, None se falhar
        """
        try:
            nome = caminho.stem
            return ArquivoInfo(
                nome=nome,
                caminho_completo=str(caminho),
                extensao=caminho.suffix.lstrip('.'),
                tamanho=caminho.stat().st_size
            )
        except OSError as e:
            logger.error(f"Erro ao processar arquivo {caminho}: {e}")
            return None

    @staticmethod
    def validar_diretorio(diretorio: Path) -> None:
        """
        Valida se o diretório existe e é realmente um diretório.
        
        Args:
            diretorio: Path do diretório a ser validado
            
        Raises:
            ValueError: Se o diretório não for válido
        """
        if not diretorio.exists():
            raise ValueError(f"Diretório não encontrado: {diretorio}")
        
        if not diretorio.is_dir():
            raise ValueError(f"O caminho especificado não é um diretório: {diretorio}")

    @staticmethod
    def listar_arquivos_by_path(diretorio: str) -> Dict[str, Dict[str, Any]]:
        """
        Lista todos os arquivos em um diretório e suas subpastas.
        
        Args:
            diretorio: Caminho do diretório a ser analisado
        
        Returns:
            Dicionário com informações dos arquivos encontrados
        
        Raises:
            ValueError: Se o diretório não existir
        """
        caminho = Path(diretorio)
        GerenciadorArquivos.validar_diretorio(caminho)
        
        arquivos_info: Dict[str, Dict[str, Any]] = {}
        
        try:
            for arquivo_path in caminho.rglob('*'):
                if arquivo_path.is_file():
                    info = GerenciadorArquivos.obter_info_arquivo(arquivo_path)
                    if info:
                        arquivos_info[arquivo_path.name] = {
                            'nome': info.nome,
                            'caminho_completo': info.caminho_completo,
                            'extensao': info.extensao,
                            'tamanho': info.tamanho
                        }
            
            logger.info(f"Processados {len(arquivos_info)} arquivos em {diretorio}")
            return arquivos_info
        
        except Exception as e:
            logger.error(f"Erro ao processar diretório {diretorio}: {e}")
            raise

    @staticmethod
    def exibir_resultado(resultado: Dict[str, Dict[str, Any]]) -> None:
        """
        Exibe o resultado da análise dos arquivos de forma formatada.
        
        Args:
            resultado: Dicionário com as informações dos arquivos
        """
        for nome, info in resultado.items():
            print(f"\nArquivo: {nome}")
            for chave, valor in info.items():
                print(f"  {chave}: {valor}")


    @staticmethod
    def gerar_nome_arquivo_temp(base: str, extensao: str) -> str:
        """
        Gera um nome único para arquivos temporários baseado em um hash.
        
        Args:
            base: String base para o hash (ex: nome do usuário, timestamp).
        
        Returns:
            Nome do arquivo com o hash.
        """
        # Combine a string base com o timestamp atual
        dados = f"{base}_{time.time()}".encode("utf-8")
        
        # Gere um hash SHA-256 a partir dos dados
        hash_obj = hashlib.sha256(dados)
        hash_str = hash_obj.hexdigest()  # Convertendo para hexadecimal
        
        # Retorne o nome do arquivo com o hash
        return f"temp_{hash_str}.{extensao}"



class StringUtils:
    @staticmethod
    def remover_caracteres(texto: str, char1: str, char2: str) -> str:
        """
        Remove os caracteres de uma string entre as primeiras ocorrências de char1 e char2.

        Args:
            texto (str): A string de entrada.
            char1 (str): O caractere inicial da substring a ser mantida.
            char2 (str): O caractere final da substring a ser mantida.

        Returns:
            str: A substring entre char1 e char2, ou a string original se char1 ou char2 não forem encontrados.
        """

        # Verificar se char1 e char2 são de fato caracteres individuais
        if len(char1) != 1 or len(char2) != 1:
            logging.error("Os parâmetros 'char1' e 'char2' devem ser caracteres individuais.")
            return texto
        
        # Verifica se os caracteres existem no texto
        if char1 not in texto:
            logging.info(f"Caractere '{char1}' não encontrado no texto.")
        if char2 not in texto:
            logging.info(f"Caractere '{char2}' não encontrado no texto.")

        try:
            # Encontrar os índices das ocorrências dos caracteres
            try:
                indice1 = texto.find(char1)
                indice2 = texto.rfind(char2)
            except Exception as e:
                return texto
            

            # Retorna a substring entre char1 e char2 (inclusive)
            return texto[indice1:indice2 + 1]
        
        except Exception as e:
            # Loga o erro caso um dos caracteres não seja encontrado
            logging.error(f"Erro ao procurar os caracteres '{char1}' e '{char2}' na string: {e}")
            # Retorna a string original
            return texto

