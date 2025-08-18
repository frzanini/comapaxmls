import os
import time
import json
import base64
import requests
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Union, Optional, Tuple

from utils.functions import GerenciadorArquivos
from dfe.DocumentoFiscalParser import DocumentoFiscalParser
from upload_dfe_s3 import upload_string_to_s3  # importa função nova

from dotenv import load_dotenv
import os

# Caminho absoluto para o .env na raiz do projeto
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=os.path.abspath(env_path))


# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sieg_api.log"),
        logging.StreamHandler()
    ]
)

class XmlType(Enum):
    NFE = 1
    CTE = 2
    NFSE = 3
    NFCE = 4
    CFE = 5

class SiegApiHandler:
    """
    Classe para gerenciar interações com a API da Sieg e processar os arquivos retornados.
    """

    def __init__(self):
        # Carregar variáveis de ambiente
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        #load_dotenv(dotenv_path=env_path)

        self.api_key = os.getenv("SIEG_API_KEY")
        self.base_url = os.getenv("URL_BAIXAR_XMLS")

        if not self.api_key or not self.base_url:
            logging.error("API_KEY ou URL_BAIXAR_XMLS não encontrados no arquivo .env.")
            raise ValueError("API_KEY ou URL_BAIXAR_XMLS não encontrados no arquivo .env.")
        
        logging.info("API Handler inicializado com sucesso.")

    def _build_payload(self, xml_type: int, take: int = 50, skip: int = 0, 
                       downloadevent: bool = False,
                       data_emissao_inicio: Optional[datetime] = None, 
                       data_emissao_fim: Optional[datetime] = None) -> dict:
        """
        Constrói o payload para a chamada à API.
        """
        data_emissao_inicio = data_emissao_inicio or datetime.now()
        data_emissao_fim = data_emissao_fim or datetime.now()

        payload = {
            "XmlType": xml_type,
            "Take": take,
            "Skip": skip,
            "DataEmissaoInicio": data_emissao_inicio.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "DataEmissaoFim": data_emissao_fim.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "Downloadevent": downloadevent
        }
        logging.debug(f"Payload construído: {payload}")
        return payload

    def _build_payload_nfse(self, xml_type: int, take: int = 50, skip: int = 0, 
                       data_emissao_inicio: Optional[datetime] = None, 
                       data_emissao_fim: Optional[datetime] = None) -> dict:
        """
        Constrói o payload para a chamada à API.
        """
        data_emissao_inicio = data_emissao_inicio or datetime.now()
        data_emissao_fim = data_emissao_fim or datetime.now()

        payload = {
            "XmlType": xml_type,
            "Take": take,
            "Skip": skip,
            "DataEmissaoInicio": data_emissao_inicio.strftime("%Y-%m-%d"),
            "DataEmissaoFim": data_emissao_fim.strftime("%Y-%m-%d")
        }
        logging.debug(f"Payload construído: {payload}")
        return payload


    def get_base64_data(self, payload: dict) -> Optional[str]:
        """
        Faz uma chamada à API para obter os dados codificados em Base64.
        """
        url = f"{self.base_url}?api_key={self.api_key}"
        logging.info(f"Enviando requisição para URL: {url}")
        logging.info(f"Payload: {payload}")

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            logging.info(f"Resposta recebida com sucesso: {response.status_code}")
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Erro ao se comunicar com a API: {e}")
            return None

    def process_and_save_base64x(self, json_data: Union[str, dict, list]) -> Tuple[int, int]:
        """
        Processa itens base64 e envia os arquivos XML diretamente para o bucket S3.
        Retorna: (total_documentos_recebidos, total_documentos_importados)
        """
        try:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
            if not isinstance(data, list):
                raise ValueError("O JSON deve ser uma lista de documentos base64.")
            logging.info(f"Dados carregados para processamento. Total de itens: {len(data)}")
        except json.JSONDecodeError:
            logging.error("Dados fornecidos não são um JSON válido.")
            raise ValueError("Dados fornecidos não são um JSON válido.")

        bucket_name = os.getenv("S3_BUCKET")
        if not bucket_name:
            raise EnvironmentError("❌ Variável de ambiente S3_BUCKET não definida.")

        total_documentos = len(data)
        total_importados = 0

        for idx, item in enumerate(data, start=1):
            try:
                texto_decodificado = base64.b64decode(item).decode('utf-8')

                parserDFe = DocumentoFiscalParser()
                resultado = parserDFe.parse_documento_fiscal_string(texto_decodificado)

                if not isinstance(resultado, dict) or "erro" in resultado:
                    logging.warning(f"Documento inválido na posição {idx}, ignorado.")
                    continue

                chave_acesso = resultado.get("chave_acesso")
                cnpj_emitente = resultado.get("cnpj_emitente")
                cnpj = resultado.get("cnpj")
                cpf = resultado.get("cpf_emitente") if not cnpj else cnpj
                data_emissao = resultado.get("data_emissao", "")[:10]
                data_evento = resultado.get("data_evento", "")[:10]

                if not cnpj_emitente:
                    logging.warning(f"CNPJ do emitente ausente, Chave {chave_acesso} | item {idx}.")
                    if cnpj:
                        cnpj_emitente = cnpj
                    elif cpf:
                        cnpj_emitente = cpf
                    else:
                        logging.warning(f"CNPJ e CPF ausentes, Chave {chave_acesso} | item {idx}, ignorado.")
                        continue

                if resultado.get("isevent") == "1":
                    if not data_evento:
                        logging.warning(f"Data do evento ausente, Chave {chave_acesso} | item {idx}, ignorado.")
                        continue
                    data_emissao = data_evento
                else:
                    if not data_emissao:
                        logging.warning(f"Data de emissão ausente, Chave {chave_acesso} | item {idx}, ignorado.")
                        continue

                # Nome do arquivo
                if resultado.get("isevent") == "1":
                    file_name = f"{resultado['chave_acesso']}_{resultado['tipo_documento']}_{resultado['tipo_evento']}_{resultado['sequencia_evento']}.xml"
                else:
                    file_name = f"{resultado['chave_acesso']}_{resultado['tipo_documento']}.xml"

                # Upload para S3 e contar somente se sucesso
                if upload_string_to_s3(
                    bucket_name=bucket_name,
                    content=texto_decodificado,
                    cnpj_emit=cnpj_emitente,
                    data_emissao=data_emissao,
                    file_name=file_name
                    ):
                    total_importados += 1

            except Exception as e:
                logging.error(f"Erro ao processar item {idx}: {type(e).__name__} - {e}")

        logging.info(f"Processamento concluído: {total_importados}/{total_documentos} documentos importados.")
        return total_documentos, total_importados

    def process_and_save_base64_(self, json_data: Union[str, dict, list], output_dir: str):
        """
        Processa o JSON contendo itens Base64 e salva os arquivos decodificados.
        """
        try:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
            logging.info(f"Dados carregados para processamento. Total de itens: {len(data)}")
        except json.JSONDecodeError:
            logging.error("Dados fornecidos não são um JSON válido.")
            raise ValueError("Dados fornecidos não são um JSON válido.")

        os.makedirs(output_dir, exist_ok=True)
        #output_dir2 = output_dir+"eventos"
        #os.makedirs(output_dir+"\\eventos", exist_ok=True)

        contador = 1

        for item in data:
            try:

                local_dir = output_dir
                #decoded_content = base64.b64decode(item)
                texto_decodificado = base64.b64decode(item).decode('utf-8')

                parserDFe = DocumentoFiscalParser()
                resultado = parserDFe.parse_documento_fiscal_string(texto_decodificado)

                if "cnpj_emitente" in resultado :
                    local_dir = f"{output_dir}\\{resultado['cnpj_emitente']}"
                    os.makedirs(local_dir, exist_ok=True)
                    #os.makedirs(local_dir+"\\eventos", exist_ok=True)
                else:
                    continue

                #print(resultado)
                #continue
                file_name = ""
                if not isinstance(resultado, dict) or "erro" in resultado:
                    file_name = GerenciadorArquivos.gerar_nome_arquivo_temp(str(contador),"xml")
                    logging.error(f"Arquivo sem parse: {file_name}")
                    #resultado['isevent'] = '1'
                elif "isevent" in resultado:
                    if resultado['isevent'] == '1':
                        file_name = f"{resultado['chave_acesso']}_{resultado['tipo_documento']}_{resultado['tipo_evento']}_{resultado['sequencia_evento']}.xml"
                        file_path = os.path.join(local_dir+"\\eventos", file_name)
                    else:
                        file_name = file_name = f"{resultado['chave_acesso']}_{resultado['tipo_documento']}.xml"
                        file_path = os.path.jodin(local_dir, file_name)
                else:
                    file_name = file_name = f"{resultado['chave_acesso']}_{resultado['tipo_documento']}.xml"
                    file_path = os.path.join(local_dir, file_name)
                try:

                    with open(file_path, "wb") as xml_file:
                        xml_file.write(texto_decodificado.encode("utf-8"))
                    logging.info(f"Arquivo salvo com sucesso: {file_path}")
                    contador += 1
                except OSError as e:
                    logging.error(f"Erro ao salvar o arquivo: {e}")
                    #logging.error(f"Erro ao salvar o arquivo: {xml_file}")
            except (base64.binascii.Error, TypeError) as e:
                # Registrar o tipo de erro e a mensagem associada
                logging.warning(f"Erro ao decodificar o item na posição {contador}: {type(e).__name__} - {e}")


    def process_and_save_base64(self, json_data: Union[str, dict, list]):
        """
        Processa itens base64 e envia os arquivos XML diretamente para o bucket S3 (sem salvar em disco).
        """
        try:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
            logging.info(f"Dados carregados para processamento. Total de itens: {len(data)}")
        except json.JSONDecodeError:
            logging.error("Dados fornecidos não são um JSON válido.")
            raise ValueError("Dados fornecidos não são um JSON válido.")

        bucket_name = os.getenv("S3_BUCKET")
        if not bucket_name:
            raise EnvironmentError("❌ Variável de ambiente S3_BUCKET não definida.")

        contador = 1
        qtde_dfe = len(data);
        logging.info(f"Total de DFe a serem processados: {qtde_dfe}")

        for item in data:
            try:
                texto_decodificado = base64.b64decode(item).decode('utf-8')

                parserDFe = DocumentoFiscalParser()
                resultado = parserDFe.parse_documento_fiscal_string(texto_decodificado)

                if not isinstance(resultado, dict) or "erro" in resultado:
                    logging.warning(f"Documento inválido na posição {contador}, ignorado.")
                    contador += 1
                    continue
                
                chave_acesso = resultado.get("chave_acesso")
                cnpj_emitente = resultado.get("cnpj_emitente")
                cnpj = resultado.get("cnpj")
                cpf = resultado.get("cpf_emitente") if not cnpj else cnpj
                data_emissao = resultado.get("data_emissao", "")[:10]  # formato YYYY-MM-DD
                data_evento = resultado.get("data_evento", "")[:10] 

                
                if not cnpj_emitente:
                    logging.warning(f"CNPJ do emitente ausente, Chave {chave_acesso} | item {contador}.")

                    if cnpj:
                        cnpj_emitente = cnpj
                    elif cpf:
                        cnpj_emitente = cpf
                    else:
                        logging.warning(f"CNPJ e CPF ausentes, Chave {chave_acesso} | item {contador}, ignorado.")
                        contador += 1
                        continue

                if resultado.get("isevent") == "1":
                    if not data_evento:
                        logging.warning(f"Data do evento ausente, Chave {chave_acesso} | item {contador}, ignorado.")
                        contador += 1
                        continue
                    data_emissao = data_evento  # Usa a data do evento se for um evento
                else:
                    if not data_emissao:
                        logging.warning(f"Data de emissão ausente, Chave {chave_acesso} | item {contador}, ignorado.")
                        contador += 1
                        continue

                # Nome do arquivo
                if resultado.get("isevent") == "1":
                    file_name = f"{resultado['chave_acesso']}_{resultado['tipo_documento']}_{resultado['tipo_evento']}_{resultado['sequencia_evento']}.xml"
                else:
                    file_name = f"{resultado['chave_acesso']}_{resultado['tipo_documento']}.xml"

                # Upload direto do conteúdo
                upload_string_to_s3(
                    bucket_name=bucket_name,
                    content=texto_decodificado,
                    cnpj_emit=cnpj_emitente,
                    data_emissao=data_emissao,
                    file_name=file_name,
                )

                logging.info(f"✅ Upload do XML {file_name} concluído.")

            except Exception as e:
                logging.error(f"Erro ao processar item {contador}: {type(e).__name__} - {e}")
            finally:
                contador += 1

        return qtde_dfe


    def download_nfse(self, start_date: datetime, end_date: datetime):
        payload = self._build_payload_nfse(int(XmlType.NFSE.value), data_emissao_inicio=start_date, data_emissao_fim=end_date)

        time.sleep(3)
        base64_data = self.get_base64_data(payload)
        if base64_data:
            self.process_and_save_base64(base64_data)
        else:
            logging.info(f"Nenhum dado encontrado para {start_date} e {end_date} e tipo {XmlType.NFSE}.")



    def download_skip(self, start_date: datetime, end_date: datetime, downloadevent: bool = False):
        """
        Faz o download dos arquivos XML para o intervalo de datas fornecido.
        Paginação por skip (0, 50, 100, ...) apenas quando o lote retornar >= 50 itens.
        Respeita intervalo de 3s entre chamadas.
        """
        # normaliza início para 00:00 do dia
        janela_inicio = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        while janela_inicio.date() <= end_date.date():
            # janela diária: 00:00 → 23:59:59
            janela_fim = janela_inicio.replace(hour=23, minute=59, second=59, microsecond=0)

            total_recebidos = 0
            total_importados = 0

            for xml_type in XmlType:
                # if xml_type != XmlType.NFE:
                #     continue
                if xml_type == XmlType.NFSE:
                    continue

                skip = 0
                while True:
                    payload = self._build_payload(
                        xml_type.value, downloadevent=downloadevent,
                        data_emissao_inicio=janela_inicio,
                        data_emissao_fim=janela_fim,
                        skip=skip,
                    )
                    logging.info(f"Payload {xml_type.name} (skip={skip}): {payload}")

                    time.sleep(3)  # intervalo entre chamadas
                    base64_data = self.get_base64_data(payload)

                    if not base64_data:
                        logging.info(
                            f"Sem dados (skip={skip}) para {xml_type.name} "
                            f"{janela_inicio}–{janela_fim}."
                        )
                        break

                    recebidos, importados = self.process_and_save_base64x(base64_data)
                    total_recebidos += recebidos
                    total_importados += importados

                    # só continua se o lote recebido tiver 50 ou mais
                    if recebidos < 50:
                        break

                    # avança o skip pelo tamanho real do lote
                    skip += recebidos

            logging.info(
                f"✅ Dia {janela_inicio:%Y-%m-%d} concluído: "
                f"recebidos={total_recebidos}, importados={total_importados}"
            )

            # próximo dia (saída do while externo "pela data mesmo")
            janela_inicio = (janela_inicio + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )


    def download_xmls(self, start_date: datetime, end_date: datetime):
        """
        Faz o download dos arquivos XML para o intervalo de datas fornecido.
        """
        for day_offset in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=day_offset)
            logging.info(f"Processando dia {current_date}...")

            #main_dir = os.path.join(
            #    os.getcwd(), "temp", str(current_date.year), 
            #    f"{current_date.month:02}", f"{current_date.day:02}"
            #)

            #os.makedirs(main_dir, exist_ok=True)

            for xml_type in XmlType:

                # if xml_type != XmlType.NFE:
                #     continue

                if xml_type == XmlType.NFSE:
                    continue

                #output_dir = os.path.join(main_dir, xml_type.name)
                #os.makedirs(output_dir, exist_ok=True)

                # Início do horário em 00:00
                hora_atual = datetime.strptime("00:00", "%H:%M")
                intervalo2 = timedelta(hours=2) ## NA VERDADE SÃO 2, MINUTOS=59 SEGUNDOS=59
                intervalo1 = timedelta(hours=1)

                # Laço para gerar 12 intervalos
                for i in range(12):
                    #hora_inicio = hora_atual.strptime("00:00", "%H:%M")  # Formata a hora de início
                    #hora_fim = (hora_atual + intervalo - timedelta(minutes=1)).strptime("00:00", "%H:%M")  # Hora final ajustada para 23:59 no último minuto
                    #logging.info(f"Intervalo {i+1}: {hora_inicio} - {hora_fim}")

                    # Concatena as horas à data_base usando replace
                    data_hora_inicio = current_date.replace(hour=hora_atual.hour, minute=hora_atual.minute, second=0)
                    data_hora_fim = current_date.replace(hour=(hora_atual + intervalo1).hour, minute=59, second=59)

                    payload = self._build_payload(xml_type.value, data_emissao_inicio=data_hora_inicio, data_emissao_fim=data_hora_fim)
                    logging.info(f"Payload para {xml_type.name}: {payload}")

                    time.sleep(3)
                    base64_data = self.get_base64_data(payload)
                    if base64_data:
                        self.process_and_save_base64(base64_data)
                    else:
                        logging.info(f"Nenhum dado encontrado para {data_hora_inicio} e {data_hora_fim} e tipo {xml_type.name}.")

                    # Incrementa o horário em 2 horas
                    hora_atual += intervalo2

