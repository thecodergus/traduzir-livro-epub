import argparse, time, openai, ast
from bs4 import BeautifulSoup as bs
from ebooklib import epub
from rich import print

class ChatGPT:
    def __init__(self, key):
        self.key = key
        # Armazena a chave da API da OpenAI para ser usada nas requisições

    def translate(self, text):
        print(text)
        openai.api_key = self.key
        # Define a chave da API da OpenAI para autenticar as requisições
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                # Define o modelo a ser usado na requisição de tradução
                messages=[
                    {
                        "role": "user",
                        # Define o papel do usuário na conversa com o modelo
                        "content": f"Please help me to translate `{text}` to Brazilian Portuguese, please return only translated content not include the origin text, maintain the same formatting as the original textual list individual elements ",
                        # Define o conteúdo da mensagem a ser enviada ao modelo, que é uma solicitação de tradução para português do Brasil mantendo o mesmo formato do texto original
                    }
                ],
            )
            # Envia a requisição de tradução para a API da OpenAI
            t_text = (
                completion["choices"][0]
                .get("message")
                .get("content")
                .encode("utf8")
                .decode()
            )
            # Extrai o texto traduzido da resposta da API
            t_text = t_text.strip("\n")
            # Remove as quebras de linha do texto traduzido
            try:
                t_text = ast.literal_eval(t_text)
                # Tenta avaliar o texto traduzido como uma expressão Python literal
            except Exception:
                pass
            # Caso a avaliação falhe, ignora o erro e mantém o texto traduzido como string
            time.sleep(3)
            # Aguarda 3 segundos antes de retornar o texto traduzido para evitar requisições muito frequentes à API
        except Exception as e:
            print(str(e), "will sleep 60 seconds")
            # Caso ocorra alguma exceção na requisição à API, imprime a mensagem de erro e aguarda 60 segundos antes de tentar novamente
            time.sleep(60)
            # Repete a requisição de tradução à API
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
        return t_text
        # Retorna o texto traduzido

class BEPUB:
    def __init__(self, epub_name, key, batch_size):
        self.epub_name = epub_name
        # Armazena o nome do arquivo EPUB a ser traduzido
        self.translate_model = ChatGPT(key)
        # Inicializa a classe ChatGPT para realizar a tradução do texto
        self.origin_book = epub.read_epub(self.epub_name)
        # Lê o arquivo EPUB usando a biblioteca ebooklib
        self.batch_size = batch_size
        # Armazena o tamanho do lote de texto a ser traduzido de cada vez

    def translate_book(self):
        new_book = epub.EpubBook()
        # Cria um novo objeto do tipo EpubBook para armazenar o livro traduzido
        new_book.metadata = self.origin_book.metadata
        # Copia os metadados do livro original para o livro traduzido
        new_book.spine = self.origin_book.spine
        # Copia a coluna vertebral do livro original para o livro traduzido
        new_book.toc = self.origin_book.toc
        # Copia o sumário do livro original para o livro traduzido
        batch_p = []
        # Inicializa uma lista para armazenar os parágrafos a serem traduzidos em cada lote
        batch_count = 0
        # Inicializa um contador para controlar o tamanho do lote
        for i in self.origin_book.get_items():
            # Iteração sobre todos os itens do livro original
            if i.get_type() == 9:
                # Verifica se o item é um arquivo HTML (tipo 9 corresponde a arquivos HTML no formato EPUB)
                soup = bs(i.content, "html.parser")
                # Parseia o conteúdo do arquivo HTML usando a biblioteca BeautifulSoup
                p_list = soup.findAll("p")
                # Encontra todos os parágrafos no arquivo HTML
                for p in p_list:
                    if p.text and not p.text.isdigit():
                        # Verifica se o parágrafo contém texto e não é apenas um número
                        batch_p.append(p)
                        # Adiciona o parágrafo à lista de parágrafos a serem traduzidos
                        batch_count += 1
                        # Incrementa o contador do tamanho do lote
                        if batch_count == self.batch_size:
                            # Verifica se o tamanho do lote atingiu o limite definido
                            translated_batch = self.translate_model.translate([p.text for p in batch_p])
                            # Traduz o lote de parágrafos usando a classe ChatGPT
                            batch_p[-1].string = batch_p[-1].text + ' '.join(map(str, translated_batch))
                            # Substitui o último parágrafo do lote pelo texto traduzido
                            batch_p = []
                            # Limpa a lista de parágrafos a serem traduzidos
                            batch_count = 0
                            # Reinicia o contador do tamanho do lote
                if batch_p:
                    # Verifica se ainda há parágrafos na lista a serem traduzidos
                    translated_batch = self.translate_model.translate([p.text for p in batch_p])
                    # Traduz o lote de parágrafos restante
                    for j, c_p in enumerate(batch_p):
                        c_p.string = c_p.text + translated_batch[j]
                        # Substitui cada parágrafo pelo texto traduzido correspondente
                    batch_p = []
                    batch_count = 0
                i.content = soup.prettify().encode()
                # Atualiza o conteúdo do arquivo HTML com os parágrafos traduzidos
            new_book.add_item(i)
            # Adiciona o item atualizado ao livro traduzido
        name = self.epub_name.split(".")[0]
        # Extrai o nome base do arquivo EPUB original
        epub.write_epub(f"{name}_translated.epub", new_book, {})
        # Salva o livro traduzido em um novo arquivo EPUB

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Cria um parser de argumentos para a interface de linha de comando
    parser.add_argument(
        "--book_name",
        dest="book_name",
        type=str,
        help="your epub book name",
    )
    # Adiciona um argumento para o nome do arquivo EPUB a ser traduzido
    parser.add_argument(
        "--openai_key",
        dest="openai_key",
        type=str,
        default="",
        help="openai api key",
    )
    # Adiciona um argumento para a chave da API da OpenAI
    parser.add_argument(
        "--batch_size",
        dest="batch_size",
        type=int,
        default=2,
        choices=[2,3,4,5],
        help="the batch size paragraph for translation , max is 5",
    )
    # Adiciona um argumento para o tamanho do lote de texto a ser traduzido de cada vez
    options = parser.parse_args()
    # Parseia os argumentos da linha de comando
    OPENAI_API_KEY = options.openai_key
    if not OPENAI_API_KEY:
        raise Exception("Need openai API key, please google how to")
        # Verifica se a chave da API da OpenAI foi fornecida
    if not options.book_name.endswith(".epub"):
        raise Exception("please use epub file")
        # Verifica se o arquivo fornecido é do tipo EPUB
    e = BEPUB(options.book_name, OPENAI_API_KEY, options.batch_size)
    # Inicializa a classe BEPUB com os parâmetros fornecidos
    e.translate_book()
    # Chama o método para traduzir o livro
