import argparse, time, openai, ast
from bs4 import BeautifulSoup as bs
from ebooklib import epub
from rich import print


class ChatGPT:
    def __init__(self, key):
        # Armazena a chave da API da OpenAI para ser usada nas requisições
        self.key = key

    def translate(self, text):
        print(text)
        # Define a chave da API da OpenAI para autenticar as requisições
        openai.api_key = self.key
        try:
            # Envia a requisição de tradução para a API da OpenAI
            completion = openai.ChatCompletion.create(
                # Define o modelo a ser usado na requisição de tradução
                model="gpt-3.5-turbo",
                messages=[
                    {
                        # Define o papel do usuário na conversa com o modelo
                        "role": "user",
                        # Define o conteúdo da mensagem a ser enviada ao modelo, que é uma solicitação de tradução para português do Brasil mantendo o mesmo formato do texto original
                        "content": f"Please help me to translate `{text}` to Brazilian Portuguese, please return only translated content not include the origin text, maintain the same formatting as the original textual list individual elements ",
                    }
                ],
            )
            # Extrai o texto traduzido da resposta da API
            t_text = (
                completion["choices"][0]
                .get("message")
                .get("content")
                .encode("utf8")
                .decode()
            )
            # Remove as quebras de linha do texto traduzido
            t_text = t_text.strip("\n")
            try:
                # Tenta avaliar o texto traduzido como uma expressão Python literal
                t_text = ast.literal_eval(t_text)
            except Exception:
                # Caso a avaliação falhe, ignora o erro e mantém o texto traduzido como string
                pass
            # Aguarda 3 segundos antes de retornar o texto traduzido para evitar requisições muito frequentes à API
            time.sleep(3)
        except Exception as e:
            # Caso ocorra alguma exceção na requisição à API, imprime a mensagem de erro e aguarda 60 segundos antes de tentar novamente
            print(str(e), "will sleep 60 seconds")
            # Repete a requisição de tradução à API
            time.sleep(60)
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Please help me to translate `{text}` to Brazilian Portuguese, please return only translated content not include the origin text, maintain the same formatting as the original textual list individual elements",
                    }
                ],
            )
            t_text = (
                completion["choices"][0]
                .get("message")
                .get("content")
                .encode("utf8")
                .decode()
            )
            t_text = t_text.strip("\n")
            try:
                t_text = ast.literal_eval(t_text)
            except Exception:
                pass
        print(t_text)
        # Retorna o texto traduzido
        return t_text


class BEPUB:
    def __init__(self, epub_name, key, batch_size):
        # Armazena o nome do arquivo EPUB a ser traduzido
        self.epub_name = epub_name
        # Inicializa a classe ChatGPT para realizar a tradução do texto
        self.translate_model = ChatGPT(key)
        # Lê o arquivo EPUB usando a biblioteca ebooklib
        self.origin_book = epub.read_epub(self.epub_name)
        # Armazena o tamanho do lote de texto a ser traduzido de cada vez
        self.batch_size = batch_size

    def translate_book(self):
        # Cria um novo objeto do tipo EpubBook para armazenar o livro traduzido
        new_book = epub.EpubBook()
        # Copia os metadados do livro original para o livro traduzido
        new_book.metadata = self.origin_book.metadata
        # Copia a coluna vertebral do livro original para o livro traduzido
        new_book.spine = self.origin_book.spine
        # Copia o sumário do livro original para o livro traduzido
        new_book.toc = self.origin_book.toc
        # Inicializa uma lista para armazenar os parágrafos a serem traduzidos em cada lote
        batch_p = []
        # Inicializa um contador para controlar o tamanho do lote
        batch_count = 0
        # Iteração sobre todos os itens do livro original
        for i in self.origin_book.get_items():
            # Verifica se o item é um arquivo HTML (tipo 9 corresponde a arquivos HTML no formato EPUB)
            if i.get_type() == 9:
                # Parseia o conteúdo do arquivo HTML usando a biblioteca BeautifulSoup
                soup = bs(i.content, "html.parser")
                # Encontra todos os parágrafos no arquivo HTML
                p_list = soup.findAll("p")
                for p in p_list:
                    # Verifica se o parágrafo contém texto e não é apenas um número
                    if p.text and not p.text.isdigit():
                        # Adiciona o parágrafo à lista de parágrafos a serem traduzidos
                        batch_p.append(p)
                        # Incrementa o contador do tamanho do lote
                        batch_count += 1
                        # Verifica se o tamanho do lote atingiu o limite definido
                        if batch_count == self.batch_size:
                            # Traduz o lote de parágrafos usando a classe ChatGPT
                            translated_batch = self.translate_model.translate(
                                [p.text for p in batch_p]
                            )
                            # Substitui o último parágrafo do lote pelo texto traduzido
                            batch_p[-1].string = batch_p[-1].text + " ".join(
                                map(str, translated_batch)
                            )
                            # Limpa a lista de parágrafos a serem traduzidos
                            batch_p = []
                            # Reinicia o contador do tamanho do lote
                            batch_count = 0
                # Verifica se ainda há parágrafos na lista a serem traduzidos
                if batch_p:
                    # Traduz o lote de parágrafos restante
                    translated_batch = self.translate_model.translate(
                        [p.text for p in batch_p]
                    )
                    for j, c_p in enumerate(batch_p):
                        # Substitui cada parágrafo pelo texto traduzido correspondente
                        c_p.string = c_p.text + translated_batch[j]
                    batch_p = []
                    batch_count = 0
                # Atualiza o conteúdo do arquivo HTML com os parágrafos traduzidos
                i.content = soup.prettify().encode()
            # Adiciona o item atualizado ao livro traduzido
            new_book.add_item(i)
        # Extrai o nome base do arquivo EPUB original
        name = self.epub_name.split(".")[0]
        # Salva o livro traduzido em um novo arquivo EPUB
        epub.write_epub(f"{name}_translated.epub", new_book, {})


if __name__ == "__main__":
    # Cria um parser de argumentos para a interface de linha de comando
    parser = argparse.ArgumentParser()
    # Adiciona um argumento para o nome do arquivo EPUB a ser traduzido
    parser.add_argument(
        "--book_name",
        dest="book_name",
        type=str,
        help="your epub book name",
    )
    # Adiciona um argumento para a chave da API da OpenAI
    parser.add_argument(
        "--openai_key",
        dest="openai_key",
        type=str,
        default="",
        help="openai api key",
    )
    # Adiciona um argumento para o tamanho do lote de texto a ser traduzido de cada vez
    parser.add_argument(
        "--batch_size",
        dest="batch_size",
        type=int,
        default=2,
        choices=[2, 3, 4, 5],
        help="the batch size paragraph for translation , max is 5",
    )
    # Parseia os argumentos da linha de comando
    options = parser.parse_args()
    OPENAI_API_KEY = options.openai_key
    if not OPENAI_API_KEY:
        # Verifica se a chave da API da OpenAI foi fornecida
        raise Exception("Need openai API key, please google how to")
    if not options.book_name.endswith(".epub"):
        # Verifica se o arquivo fornecido é do tipo EPUB
        raise Exception("please use epub file")
    # Inicializa a classe BEPUB com os parâmetros fornecidos
    e = BEPUB(options.book_name, OPENAI_API_KEY, options.batch_size)
    # Chama o método para traduzir o livro
    e.translate_book()
